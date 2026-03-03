import zipfile
import os
import json
from typing import List, Dict, Any
from io import BytesIO
from datetime import datetime

class ZipPackager:
    """
    Module for packaging canonical topic artifacts into a ZIP file.
    Hardened for Determinism.
    """

    @staticmethod
    def create_package(topic_id: str, documents: List[Dict[str, Any]], manifest: Dict[str, Any], output_path: str = None) -> str:
        """
        Creates a ZIP package containing the generated documents and a manifest.
        Returns the path to the created ZIP file.
        
        Guarantees:
        1. Stable Filename Ordering
        2. Normalized Timestamps (1980-01-01)
        """
        if not output_path:
            output_path = f"output/nexus/packages/{topic_id}_canonical.zip"

        os.makedirs(os.path.dirname(output_path), exist_ok=True)

        # Deterministic Sorting of Documents
        sorted_docs = sorted(documents, key=lambda x: x["filename"])
        
        # Fixed Timestamp for ZIP Determinism (1980-01-01 00:00:00)
        fixed_dt = (1980, 1, 1, 0, 0, 0)

        with zipfile.ZipFile(output_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            # 1. Add Documents with ZipInfo
            for doc in sorted_docs:
                zinfo = zipfile.ZipInfo(doc["filename"], date_time=fixed_dt)
                zinfo.compress_type = zipfile.ZIP_DEFLATED
                zipf.writestr(zinfo, doc["content"])
            
            # 2. Add Manifest last
            zinfo_manifest = zipfile.ZipInfo("manifest.json", date_time=fixed_dt)
            zinfo_manifest.compress_type = zipfile.ZIP_DEFLATED
            zipf.writestr(zinfo_manifest, json.dumps(manifest, indent=2, sort_keys=True))

        print(f"[ZipPackager] Created package at: {output_path}")
        return output_path

    @staticmethod
    def create_in_memory_package(topic_id: str, documents: List[Dict[str, Any]]) -> BytesIO:
        """
        Creates a ZIP package in memory.
        Useful for direct API responses.
        Hardened for Determinism.
        """
        buf = BytesIO()
        fixed_dt = (1980, 1, 1, 0, 0, 0)
        
        # Deterministic Sorting of Documents
        sorted_docs = sorted(documents, key=lambda x: x["filename"])

        with zipfile.ZipFile(buf, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for doc in sorted_docs:
                info = zipfile.ZipInfo(doc["filename"], date_time=fixed_dt)
                info.compress_type = zipfile.ZIP_DEFLATED
                zipf.writestr(info, doc["content"])
            
            manifest = {
                "topic_id": topic_id,
                "document_count": len(documents),
                "filenames": sorted([doc["filename"] for doc in documents])
            }
            info_manifest = zipfile.ZipInfo("manifest.json", date_time=fixed_dt)
            info_manifest.compress_type = zipfile.ZIP_DEFLATED
            zipf.writestr(info_manifest, json.dumps(manifest, indent=2, sort_keys=True))
        
        buf.seek(0)
        return buf
