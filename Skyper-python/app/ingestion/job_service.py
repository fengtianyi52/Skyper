import asyncio
import logging
from datetime import datetime, timedelta

from app.common.time_utils import utcnow
from sqlalchemy import select, update, func, or_

from app.config import settings
from app.ingestion.models import IngestionJob
from app.ingestion.pipeline import create_ingestion_processor
from app.ingestion.errors import ingestion_error
from app.document.models import Document

logger = logging.getLogger(__name__)


class IngestionJobWorker:
    def __init__(self):
        self._running = False
        self._task: asyncio.Task | None = None
        self.worker_id = settings.ingestion.worker_id
        self.poll_interval = settings.ingestion.worker_poll_interval_seconds

    async def start(self) -> None:
        self._running = True
        self._task = asyncio.create_task(self._poll_loop())
        logger.info("IngestionJobWorker started: workerId=%s", self.worker_id)

    async def stop(self) -> None:
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        logger.info("IngestionJobWorker stopped")

    async def _poll_loop(self) -> None:
        from app.dependencies import async_session_factory

        while self._running:
            try:
                async with async_session_factory() as session:
                    result = await session.execute(
                        select(IngestionJob)
                        .where(
                            IngestionJob.status == "PENDING",
                            or_(
                                IngestionJob.next_retry_at.is_(None),
                                IngestionJob.next_retry_at <= func.now(),
                            ),
                        )
                        .order_by(IngestionJob.created_at)
                        .with_for_update(skip_locked=True)
                        .limit(1)
                    )
                    job = result.scalar_one_or_none()

                    if job:
                        await self._execute_job(session, job)
                    await session.commit()
            except asyncio.CancelledError:
                raise
            except Exception as e:
                logger.error("Job poll error: %s", e)

            await asyncio.sleep(self.poll_interval)

    async def _execute_job(self, session, job: IngestionJob) -> None:
        job_id, document_id, group_id = job.id, job.document_id, job.group_id
        retry_count, max_retries = job.retry_count, job.max_retries
        now = utcnow()
        job.status = "RUNNING"
        job.worker_id = self.worker_id
        job.started_at = now
        await session.flush()

        try:
            processor = create_ingestion_processor(session)
            await processor.process(document_id, group_id)
            job.status = "SUCCEEDED"
            job.finished_at = utcnow()
            logger.info("Job %s succeeded: docId=%s", job.id, job.document_id)
        except Exception as e:
            # SQL failures invalidate the transaction. Persist reason in a fresh one,
            # using saved IDs (ORM objects expire on rollback).
            await session.rollback()
            failure = ingestion_error(e, "文档处理")
            retry_count += 1
            retry = failure.retryable and retry_count < max_retries
            delay = 30 * (2 ** retry_count)
            reason = str(failure)
            await session.execute(update(IngestionJob).where(IngestionJob.id == job_id).values(
                status="PENDING" if retry else "FAILED",
                retry_count=retry_count, last_error=reason,
                next_retry_at=utcnow() + timedelta(seconds=delay) if retry else None,
                finished_at=None if retry else utcnow(),
            ))
            await session.execute(update(Document).where(
                Document.id == document_id, Document.deleted == False,
            ).values(
                status="PENDING" if retry else ("PARSED" if failure.waiting else "FAILED"),
                failure_reason=(f"{reason} 将在 {delay} 秒后自动重试。" if retry else reason),
            ))
            logger.warning("Job %s: %s", job_id, reason)

        await session.flush()


async def recover_interrupted_jobs() -> int:
    """On startup, mark RUNNING jobs orphaned by a previous process crash as
    FAILED and reset their documents so they can be retried from the UI."""
    from app.dependencies import async_session_factory
    from app.document.models import Document

    async with async_session_factory() as session:
        result = await session.execute(
            select(IngestionJob).where(IngestionJob.status == "RUNNING")
        )
        jobs = result.scalars().all()
        if not jobs:
            return 0

        reason = "任务中断：服务重启，请重试"
        for job in jobs:
            job.status = "FAILED"
            job.last_error = reason
            job.finished_at = utcnow()
        await session.execute(
            update(Document)
            .where(Document.id.in_([j.document_id for j in jobs]))
            .values(status="FAILED", failure_reason=reason)
        )
        await session.commit()
        logger.warning("Recovered %d interrupted ingestion jobs", len(jobs))
        return len(jobs)


worker = IngestionJobWorker()
