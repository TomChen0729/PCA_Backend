import os
from concurrent.futures import ThreadPoolExecutor

from extensions import db
from models.outfit import TryOnHistory, TryOnJob
from models.wardrobe_item import WardrobeItem
from services.vton_service import VtonService


_executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="pca-vton")


def enqueue(app, job_id):
    _executor.submit(_run, app, job_id)


def _run(app, job_id):
    with app.app_context():
        job = TryOnJob.query.get(job_id)
        if not job or job.status == "completed":
            return
        job.status, job.error = "processing", None
        db.session.commit()
        try:
            top = WardrobeItem.query.filter_by(id=job.top_item_id, uid=job.uid, tag="top", recycling_status="active").first()
            bottom = WardrobeItem.query.filter_by(id=job.bottom_item_id, uid=job.uid, tag="bottom", recycling_status="active").first()
            if not top or not bottom:
                raise ValueError("衣櫥單品已不存在，請重新選擇")
            top_path = os.path.join(app.root_path, top.imgPath)
            bottom_path = os.path.join(app.root_path, bottom.imgPath)
            if not job.top_result_id:
                job.stage, job.progress = "top", 10
                db.session.commit()
                job.top_result_id = VtonService.generate_tryon(job.human_path, top_path, str(job.uid), "upper_body")
                job.stage, job.progress = "bottom", 55
                db.session.commit()
            job.result_id = VtonService.generate_tryon(
                VtonService.get_result_path(str(job.uid), job.top_result_id), bottom_path,
                str(job.uid), "lower_body")
            job.status, job.progress, job.stage = "completed", 100, "completed"
            db.session.add(TryOnHistory(uid=job.uid, top_item_id=top.id, bottom_item_id=bottom.id, result_id=job.result_id))
            db.session.commit()
            try:
                os.remove(job.human_path)
            except OSError:
                pass
        except Exception as exc:
            db.session.rollback()
            job = TryOnJob.query.get(job_id)
            if job:
                job.status, job.error = "failed", str(exc)[:250]
                db.session.commit()
        finally:
            db.session.remove()
