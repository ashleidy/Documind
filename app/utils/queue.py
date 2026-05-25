# app/utils/queue.py
import threading
import queue
import uuid
from datetime import datetime
from typing import Callable

# ── Cola y estado ─────────────────────────────────────────────
_job_queue      = queue.Queue()
_job_results    = {}
_jobs_lock      = threading.Lock()
_worker_started = False

STATUS_PENDING    = 'pending'
STATUS_PROCESSING = 'processing'
STATUS_DONE       = 'done'
STATUS_ERROR      = 'error'


def _worker():
    """
    Worker único secuencial.
    Con Groq cada job dura 3-5 seg → la cola fluye rápido.
    Con Phi3 dura 2-3 min → los usuarios esperan más.
    """
    print("✓ Worker iniciado")
    while True:
        try:
            job_id, fn, kwargs = _job_queue.get(timeout=2)
        except queue.Empty:
            continue

        # Calcular posición en cola para el usuario
        queue_size = _job_queue.qsize()
        print(f"→ Job {job_id[:8]} | Pendientes en cola: {queue_size}")

        with _jobs_lock:
            _job_results[job_id]['status']     = STATUS_PROCESSING
            _job_results[job_id]['started_at'] = datetime.utcnow()

        try:
            result = fn(**kwargs)
            with _jobs_lock:
                _job_results[job_id]['status']      = STATUS_DONE
                _job_results[job_id]['result']       = result
                _job_results[job_id]['finished_at']  = datetime.utcnow()
            print(f"✓ Job {job_id[:8]} completado — modelo: {result.get('model','?')}")

        except Exception as e:
            print(f"✗ Job {job_id[:8]} error: {e}")
            with _jobs_lock:
                _job_results[job_id]['status'] = STATUS_ERROR
                _job_results[job_id]['error']  = str(e)

        finally:
            _job_queue.task_done()


def start_worker():
    global _worker_started
    if _worker_started:
        return
    _worker_started = True
    t = threading.Thread(target=_worker, daemon=True, name="DocuMind-Worker")
    t.start()


def enqueue(fn: Callable, **kwargs) -> str:
    _cleanup_old_jobs()
    job_id     = str(uuid.uuid4())
    queue_pos  = _job_queue.qsize() + 1  # posición aproximada

    with _jobs_lock:
        _job_results[job_id] = {
            'status':     STATUS_PENDING,
            'result':     None,
            'error':      None,
            'queue_pos':  queue_pos,
            'created_at': datetime.utcnow(),
            'started_at': None,
            'finished_at': None
        }

    _job_queue.put((job_id, fn, kwargs))
    print(f"+ Job encolado {job_id[:8]} | Pos: {queue_pos}")
    return job_id


def get_job_status(job_id: str) -> dict:
    with _jobs_lock:
        data = _job_results.get(job_id)

    if not data:
        return {'status': STATUS_ERROR, 'error': 'Job no encontrado'}

    # Calcular tiempo esperando
    elapsed = 0
    if data['created_at']:
        elapsed = int((datetime.utcnow() - data['created_at']).total_seconds())

    return {
        'status':    data['status'],
        'result':    data['result'],
        'error':     data['error'],
        'queue_pos': data['queue_pos'],
        'elapsed':   elapsed,          # segundos esperando
        'pending':   _job_queue.qsize() # cuántos hay delante
    }


def _cleanup_old_jobs():
    now = datetime.utcnow()
    with _jobs_lock:
        viejos = [
            jid for jid, d in _job_results.items()
            if (now - d['created_at']).total_seconds() > 3600
        ]
        for jid in viejos:
            del _job_results[jid]