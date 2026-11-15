"""Export the locked report with its NumPy decision boolean converted to a JSON boolean.

Run from schema-native: .venv/bin/python analysis/e0b-amendment3-v1/export_report.py
No inference, scoring changes or statistical-rule changes. Original sn/ source stays frozen.
"""
from pathlib import Path
import json
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
from sn import e0b_report
from sn.e0b import config


def main():
    original=e0b_report.comparisons
    def json_boolean(rows,rc):
        result=original(rows,rc)
        result['order_effect_rule_met']=bool(result['order_effect_rule_met'])
        return result
    e0b_report.comparisons=json_boolean
    try:
        result=e0b_report.report('e0b-amendment3-v1',config())
    finally:
        e0b_report.comparisons=original
    print(json.dumps(result,indent=2))


if __name__=='__main__':main()
