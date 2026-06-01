import asyncio
import time
from pathlib import Path

import httpx
import numpy as np
from loguru import logger

API_URL = "http://127.0.0.1:8000"

async def upload_and_wait(client: httpx.AsyncClient, pdf_path: Path, user_id: int) -> dict:
    file_bytes = pdf_path.read_bytes()
    
    unique_marker = f"\n% DUMMY FOR USER {user_id} TIMESTAMP {time.time()}\n".encode('utf-8')
    file_bytes += unique_marker
    
    result = {
        "success": False,
        "api_response_time": 0.0,
        "ingestion_time": 0.0,
        "error_message": None
    }
    
    start_time = time.time()
    try:
        api_start = time.time()
        res = await client.post(
            f"{API_URL}/ingest/upload",
            files={"file": (f"user_{user_id}.pdf", file_bytes, "application/pdf")},
            data={"force": "true"}
        )
        res.raise_for_status()
        result["api_response_time"] = time.time() - api_start
        
        data = res.json()
        doc_id = data.get("doc_id")
        
        while True:
            await asyncio.sleep(2.0)
            status_res = await client.get(f"{API_URL}/ingest/status/{doc_id}")
            
            if status_res.status_code == 200:
                status_data = status_res.json()
                if status_data["status"] == "completed":
                    result["ingestion_time"] = time.time() - start_time
                    result["success"] = True
                    logger.success(f"User {user_id:02d} | SUCCESS | Total: {result['ingestion_time']:.2f}s | API: {result['api_response_time']:.2f}s")
                    return result
                elif status_data["status"] == "failed":
                    result["ingestion_time"] = time.time() - start_time
                    result["error_message"] = status_data.get('message', 'Unknown error in pipeline')
                    logger.error(f"User {user_id:02d} | FAILED | {result['error_message']}")
                    return result
            elif status_res.status_code == 404:
                result["ingestion_time"] = time.time() - start_time
                result["error_message"] = f"Task {doc_id} NOT FOUND"
                logger.error(f"User {user_id:02d} | NOT FOUND | Task {doc_id} biến mất do Crash/OOM?")
                return result
                
    except Exception as e:
        result["ingestion_time"] = time.time() - start_time
        result["error_message"] = str(e)
        logger.error(f"User {user_id:02d} | HTTP ERROR | {e}")
        return result

async def run_batch(concurrency: int, pdf_path: Path):
    logger.info("==================================================")
    logger.info(f"KÍCH HOẠT BATCH: {concurrency} CONCURRENT UPLOADS")
    logger.info("==================================================")
    
    batch_start_time = time.time()
    
    async with httpx.AsyncClient(timeout=600.0) as client:
        tasks = [upload_and_wait(client, pdf_path, i+1) for i in range(concurrency)]
        results = await asyncio.gather(*tasks)
        
    total_benchmark_time = time.time() - batch_start_time

    success_results = [r for r in results if r["success"]]
    failed_results = [r for r in results if not r["success"]]
    
    success_count = len(success_results)
    failed_count = len(failed_results)
    
    api_times = [r["api_response_time"] for r in results if r["api_response_time"] > 0]
    ingest_times = [r["ingestion_time"] for r in success_results]
    error_messages = [r["error_message"] for r in failed_results if r["error_message"]]
    
    avg_api_time = np.mean(api_times) if api_times else 0.0
    avg_ingestion_time = np.mean(ingest_times) if ingest_times else 0.0
    p95_ingestion_time = np.percentile(ingest_times, 95) if ingest_times else 0.0
    
    throughput = (success_count / total_benchmark_time) * 60 if total_benchmark_time > 0 else 0.0

    logger.warning(f"--- BÁO CÁO BATCH {concurrency} USERS ---")
    logger.info(f"Success Count        : {success_count}")
    logger.info(f"Failed Count         : {failed_count}")
    logger.info(f"Total Benchmark Time : {total_benchmark_time:.2f}s")
    logger.info(f"Average API Time     : {avg_api_time:.2f}s")
    
    if success_count > 0:
        logger.info(f"Avg Ingestion Time   : {avg_ingestion_time:.2f}s")
        logger.info(f"P95 Ingestion Time   : {p95_ingestion_time:.2f}s")
        logger.info(f"Throughput           : {throughput:.2f} files/minute")
        
    if failed_count > 0:
        logger.error(f"Errors Found:")
        unique_errors = set(error_messages)
        for err in unique_errors:
            logger.error(f"  - {err} (x{error_messages.count(err)})")
            
    print("\n")

async def main():
    pdf_path = next(Path("cvpr_papers_by_topic").rglob("*.pdf"), None)
    if not pdf_path:
        logger.error("Không tìm thấy file PDF nào trong 'cvpr_papers_by_topic/'. Hãy copy một file PDF vào dự án.")
        return
        
    logger.info(f"Sử dụng file PDF làm payload: {pdf_path.name}")
    
    batches = [5, 10, 15, 20]
    
    for b in batches:
        await run_batch(b, pdf_path)
        if b != batches[-1]:
            logger.info("Nghỉ ngơi 60s trước khi qua Batch tiếp theo cho server hạ nhiệt...\n")
            await asyncio.sleep(60)

if __name__ == "__main__":
    asyncio.run(main())
