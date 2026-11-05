import json
import os
import threading


class TaskStore:
    def __init__(self, path: str):
        self.path = path
        self.lock = threading.Lock()
        self.data = {}
        self._reload()

    def _reload(self):
        with self.lock:
            if os.path.exists(self.path):
                try:
                    with open(self.path, "r", encoding="utf-8") as f:
                        self.data = json.load(f)
                except (json.JSONDecodeError, OSError):
                    pass

    def _save(self):
        # 注意：调用方已持有 self.lock，这里不能再加锁（非重入锁会死锁）
        os.makedirs(os.path.dirname(self.path), exist_ok=True)
        tmp = self.path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(self.data, f, ensure_ascii=False, indent=2)
        os.replace(tmp, self.path)

    def add(self, task: dict):
        self._reload()
        with self.lock:
            self.data[task["id"]] = task
            self._save()

    def update(self, task_id: str, **fields):
        self._reload()
        with self.lock:
            if task_id in self.data:
                self.data[task_id].update(fields)
                self._save()

    def get(self, task_id: str):
        self._reload()
        with self.lock:
            return self.data.get(task_id)

    def list(self):
        self._reload()
        with self.lock:
            items = list(self.data.values())
        items.sort(key=lambda t: t.get("created_at", 0), reverse=True)
        return items

    def delete(self, task_id: str):
        self._reload()
        with self.lock:
            if task_id in self.data:
                del self.data[task_id]
                self._save()
                return True
        return False


def public_task(task: dict) -> dict:
    return {k: v for k, v in task.items() if k not in ("request",)}


class ChainJobStore:
    """批量生成任务（含尾帧衔接）的本地存储。"""

    def __init__(self, path: str):
        self.path = path
        self.lock = threading.Lock()
        self.data = {}
        if os.path.exists(path):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    self.data = json.load(f)
            except (json.JSONDecodeError, OSError):
                self.data = {}

    def _save(self):
        os.makedirs(os.path.dirname(self.path), exist_ok=True)
        tmp = self.path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(self.data, f, ensure_ascii=False, indent=2)
        os.replace(tmp, self.path)

    def add(self, job: dict):
        with self.lock:
            self.data[job["id"]] = job
            self._save()

    def get(self, job_id: str):
        with self.lock:
            return self.data.get(job_id)

    def update(self, job_id: str, **fields):
        with self.lock:
            if job_id in self.data:
                self.data[job_id].update(fields)
                self._save()

    def update_item(self, job_id: str, index: int, **fields):
        with self.lock:
            job = self.data.get(job_id)
            if job and 0 <= index < len(job["items"]):
                job["items"][index].update(fields)
                self._save()

    def list(self):
        with self.lock:
            items = list(self.data.values())
        items.sort(key=lambda j: j.get("created_at", 0), reverse=True)
        return items

    def delete(self, job_id: str):
        with self.lock:
            if job_id in self.data:
                del self.data[job_id]
                self._save()
                return True
        return False


class ExtendJobStore:
    """长片延长任务的本地存储。"""

    def __init__(self, path: str):
        self.path = path
        self.lock = threading.Lock()
        self.data = {}
        if os.path.exists(path):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    self.data = json.load(f)
            except (json.JSONDecodeError, OSError):
                self.data = {}

    def _save(self):
        os.makedirs(os.path.dirname(self.path), exist_ok=True)
        tmp = self.path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(self.data, f, ensure_ascii=False, indent=2)
        os.replace(tmp, self.path)

    def add(self, job: dict):
        with self.lock:
            self.data[job["id"]] = job
            self._save()

    def get(self, job_id: str):
        with self.lock:
            return self.data.get(job_id)

    def update(self, job_id: str, **fields):
        with self.lock:
            if job_id in self.data:
                self.data[job_id].update(fields)
                self._save()

    def list(self):
        with self.lock:
            items = list(self.data.values())
        items.sort(key=lambda j: j.get("created_at", 0), reverse=True)
        return items

    def delete(self, job_id: str):
        with self.lock:
            if job_id in self.data:
                del self.data[job_id]
                self._save()
                return True
        return False

class ImageJobStore:
    """图片生成任务的本地存储（后台异步）。"""

    def __init__(self, path: str):
        self.path = path
        self.lock = threading.Lock()
        self.data = {}
        if os.path.exists(path):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    self.data = json.load(f)
            except (json.JSONDecodeError, OSError):
                self.data = {}

    def _save(self):
        os.makedirs(os.path.dirname(self.path), exist_ok=True)
        tmp = self.path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(self.data, f, ensure_ascii=False, indent=2)
        os.replace(tmp, self.path)

    def add(self, job: dict):
        with self.lock:
            self.data[job["id"]] = job
            self._save()

    def get(self, job_id: str):
        with self.lock:
            return self.data.get(job_id)

    def update(self, job_id: str, **fields):
        with self.lock:
            if job_id in self.data:
                self.data[job_id].update(fields)
                self._save()

    def list(self):
        with self.lock:
            items = list(self.data.values())
        items.sort(key=lambda j: j.get("created_at", 0), reverse=True)
        return items

    def delete(self, job_id: str):
        with self.lock:
            if job_id in self.data:
                del self.data[job_id]
                self._save()
                return True
        return False
