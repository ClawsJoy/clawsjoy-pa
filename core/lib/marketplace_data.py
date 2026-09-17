#!/usr/bin/env python3
"""Marketplace Data - Marketplace Data 模块

@version: 5.0.0
@author: ClawsJoy
@date: 2026-5-31
"""


import json
from pathlib import Path
from typing import Dict, List, Optional

from core.lib.unified_config import unified_config


class MarketplaceData:
    def __init__(self):
        data_root = unified_config.get("paths.data_root", "data")
        self.marketplace_dir = Path(f"{data_root}/marketplace")
        self.marketplace_dir.mkdir(parents=True, exist_ok=True)
        self._load_data()

    def _load_data(self):
        self.products = {}
        for json_file in self.marketplace_dir.glob("*.json"):
            try:
                with open(json_file, "r") as f:
                    product = json.load(f)
                    product_id = json_file.stem
                    self.products[product_id] = product
            except Exception as e:
                pass

    def get_product(self, product_id: str) -> Optional[Dict]:
        return self.products.get(product_id)

    def list_products(self) -> List[Dict]:
        return list(self.products.values())

    def add_product(self, product_id: str, product_data: Dict) -> bool:
        file_path = self.marketplace_dir / f"{product_id}.json"
        with open(file_path, "w") as f:
            json.dump(product_data, f, indent=2)
        self.products[product_id] = product_data
        return True


marketplace_data = MarketplaceData()
