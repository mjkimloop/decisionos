#!/usr/bin/env python
from __future__ import annotations

import argparse
from pathlib import Path

from apps.region.state import set_active, status


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("region", help="region name to activate")
    args = ap.parse_args()
    st = set_active(args.region)
    print({"active": st.active, "secondary": st.secondary})


if __name__ == '__main__':
    main()
