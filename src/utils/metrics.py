import threading
import numpy as np

class GlobalMetricsTracker:
    def __init__(self):
        self.lock = threading.Lock()
        self.success_uploads = 0
        self.failed_uploads = 0
        
        self.ingestion_times = []
        self.parsing_times = []
        self.embedding_times = []
        self.upsert_times = []
        
        self.peak_memory = 0.0
        
        self.cache_hits = 0
        self.cache_misses = 0

    def record_ingestion(self, success: bool, total_time: float = 0, 
                         parsing_time: float = 0, embedding_time: float = 0, 
                         upsert_time: float = 0, peak_mem: float = 0):
        with self.lock:
            if success:
                self.success_uploads += 1
                self.ingestion_times.append(total_time)
                self.parsing_times.append(parsing_time)
                self.embedding_times.append(embedding_time)
                self.upsert_times.append(upsert_time)
            else:
                self.failed_uploads += 1
                
            if peak_mem > self.peak_memory:
                self.peak_memory = peak_mem

    def record_cache(self, hit: bool):
        with self.lock:
            if hit:
                self.cache_hits += 1
            else:
                self.cache_misses += 1

    def _calc_stats(self, data: list) -> dict:
        if not data:
            return {"avg": 0.0, "p95": 0.0}
        return {
            "avg": round(float(np.mean(data)), 2),
            "p95": round(float(np.percentile(data, 95)), 2)
        }

    def get_summary(self) -> dict:
        with self.lock:
            ingest_stats = self._calc_stats(self.ingestion_times)
            parse_stats = self._calc_stats(self.parsing_times)
            embed_stats = self._calc_stats(self.embedding_times)
            upsert_stats = self._calc_stats(self.upsert_times)
            
            return {
                "success_uploads": self.success_uploads,
                "failed_uploads": self.failed_uploads,
                "ingestion_time": ingest_stats,
                "parsing_time": parse_stats,
                "embedding_time": embed_stats,
                "upsert_time": upsert_stats,
                "peak_memory_mb": round(self.peak_memory, 2),
                "cache_hits": self.cache_hits,
                "cache_misses": self.cache_misses
            }
