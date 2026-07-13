#!/usr/bin/env python3
# 为 Flutter 图文/视频流/工具包分配代码防关联组合，写入 workspace/本包代码组合.json（含 dartCodePrefix）
# 用法: alloc_code_combo.py <registry_json_path> <workspace_path>
# 读取登记表中 60 天内已用组合，分配未用或最少用的组合，并分配 IAP/举报/常量模块名

import json
import os
import random
import string
import sys
from datetime import datetime, timedelta

NAMING_STYLES = ["screen_suffix", "page_suffix", "view_suffix", "screen_prefix", "route_suffix", "container_suffix", "page_prefix", "view_prefix"]
FOLDER_STYLES = ["by_feature", "by_layer", "by_flow", "hybrid", "by_domain", "by_screen", "flat_prefix", "nested_feature"]
ARCHITECTURES = ["layered", "feature_first", "simple", "clean", "modular"]
STATE_MANAGEMENTS = ["setState", "provider", "riverpod", "bloc", "inherited"]
CODE_ORGANIZATIONS = ["fine_grained", "by_lifecycle", "by_data_flow", "hybrid", "by_screen"]
# P1: 代码维度扩展
FILE_NAMINGS = ["snake_case", "pascal_case"]
IMPORT_STYLES = ["relative", "package_prefix"]
CONSTANTS_LAYOUTS = ["single_file", "per_feature", "scattered"]

IAP_NAMES = ["CoinStore", "CreditService", "PurchaseHelper", "WalletManager", "TokenService", "GemStore", "CoinManager", "PurchaseService"]
REPORT_NAMES = ["ReportHandler", "ContentReportService", "ReportService", "AbuseReportHandler", "FeedbackReportService"]
CONSTANTS_NAMES = ["ThemeConstants", "AppFeatureFlags", "AppConfig", "ThemeConfig", "AppConstants"]
# P1: 三阶命名池（网络/路由/工具类）
NETWORK_NAMES = ["ApiClient", "NetworkService", "RequestManager", "RestHelper", "HttpClient", "ApiService", "RemoteRepository"]
ROUTER_NAMES = ["AppRouter", "NavCoordinator", "RouteMap", "FlowNavigator", "NavigationHandler", "RouteRegistry"]
UTILITY_NAMES = ["DateUtils", "FormatterHelper", "ValidationService", "StringUtils", "FormatHelper", "ValidationUtils"]

COOLDOWN_DAYS = int(os.environ.get("COOLDOWN_DAYS", 60))

PROJ_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STRATEGY_SCORES_PATH = os.path.join(PROJ_ROOT, "data", "evolution", "strategy-scores.json")


def _load_strategy_weights():
    """Load strategy health scores from evolution data for weighted selection."""
    try:
        with open(STRATEGY_SCORES_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data.get("combos", {})
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def _weighted_select(candidates, weights, workspace):
    """Select a combo weighted by health score. Higher score = more likely to be chosen."""
    if not candidates:
        return NAMING_STYLES[0], FOLDER_STYLES[0], ARCHITECTURES[0], STATE_MANAGEMENTS[0], CODE_ORGANIZATIONS[0]

    scored = []
    for c in candidates:
        key = f"{c[0]}|{c[1]}|{c[2]}|{c[3]}"
        w = weights.get(key, {}).get("health_score", 50)
        scored.append((c, max(w, 5)))

    if not any(s[1] != 50 for s in scored):
        return candidates[0]

    import random
    random.seed(hash(workspace) + int(datetime.now().strftime("%Y%m%d")))
    total = sum(s[1] for s in scored)
    r = random.uniform(0, total)
    cumulative = 0
    for combo, weight in scored:
        cumulative += weight
        if r <= cumulative:
            return combo

    return scored[0][0]


def main():
    if len(sys.argv) < 3:
        print("用法: alloc_code_combo.py <registry_json_path> <workspace_path>", file=sys.stderr)
        sys.exit(1)
    reg_path = sys.argv[1]
    workspace = sys.argv[2].rstrip("/")

    cutoff = (datetime.now() - timedelta(days=COOLDOWN_DAYS)).strftime("%Y-%m-%d")
    recent_combos = set()
    recent_iap = set()
    recent_report = set()
    recent_const = set()
    recent_file_naming = set()
    recent_import_style = set()
    recent_constants_layout = set()
    recent_network = set()
    recent_router = set()
    recent_utility = set()
    recent_dart_prefix = set()

    if os.path.isfile(reg_path):
        try:
            with open(reg_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            for p in data.get("packages") or []:
                used_at = p.get("usedAt") or p.get("registeredAt") or ""
                if used_at < cutoff:
                    continue
                cc = p.get("codeAntiCorrelation") or {}
                n, f, a, s, c = cc.get("namingStyle"), cc.get("folderStyle"), cc.get("architecture"), cc.get("stateManagement"), cc.get("codeOrganization")
                if n and f and a and s and c:
                    recent_combos.add((n, f, a, s, c))
                if cc.get("iapModuleName"):
                    recent_iap.add(cc.get("iapModuleName"))
                if cc.get("reportModuleName"):
                    recent_report.add(cc.get("reportModuleName"))
                if cc.get("constantsModuleName"):
                    recent_const.add(cc.get("constantsModuleName"))
                if cc.get("fileNaming"):
                    recent_file_naming.add(cc.get("fileNaming"))
                if cc.get("importStyle"):
                    recent_import_style.add(cc.get("importStyle"))
                if cc.get("constantsLayout"):
                    recent_constants_layout.add(cc.get("constantsLayout"))
                if cc.get("networkLayerName"):
                    recent_network.add(cc.get("networkLayerName"))
                if cc.get("routeCoordinatorName"):
                    recent_router.add(cc.get("routeCoordinatorName"))
                if cc.get("utilityHelperName"):
                    recent_utility.add(cc.get("utilityHelperName"))
                dp = cc.get("dartCodePrefix")
                if dp and isinstance(dp, str):
                    recent_dart_prefix.add(dp.lower().strip())
        except Exception:
            pass

    import itertools
    all_combos = list(itertools.product(
        NAMING_STYLES, FOLDER_STYLES, ARCHITECTURES, STATE_MANAGEMENTS, CODE_ORGANIZATIONS
    ))[:500]

    strategy_weights = _load_strategy_weights()

    available = [c for c in all_combos if c not in recent_combos]
    if not available:
        available = all_combos

    chosen = _weighted_select(available, strategy_weights, workspace)

    iap_name = next((x for x in IAP_NAMES if x not in recent_iap), IAP_NAMES[hash(workspace + "iap") % len(IAP_NAMES)])
    report_name = next((x for x in REPORT_NAMES if x not in recent_report), REPORT_NAMES[hash(workspace + "r") % len(REPORT_NAMES)])
    const_name = next((x for x in CONSTANTS_NAMES if x not in recent_const), CONSTANTS_NAMES[hash(workspace + "c") % len(CONSTANTS_NAMES)])
    file_naming = next((x for x in FILE_NAMINGS if x not in recent_file_naming), FILE_NAMINGS[hash(workspace + "fn") % len(FILE_NAMINGS)])
    import_style = next((x for x in IMPORT_STYLES if x not in recent_import_style), IMPORT_STYLES[hash(workspace + "im") % len(IMPORT_STYLES)])
    constants_layout = next((x for x in CONSTANTS_LAYOUTS if x not in recent_constants_layout), CONSTANTS_LAYOUTS[hash(workspace + "cl") % len(CONSTANTS_LAYOUTS)])
    network_name = next((x for x in NETWORK_NAMES if x not in recent_network), NETWORK_NAMES[hash(workspace + "net") % len(NETWORK_NAMES)])
    router_name = next((x for x in ROUTER_NAMES if x not in recent_router), ROUTER_NAMES[hash(workspace + "route") % len(ROUTER_NAMES)])
    utility_name = next((x for x in UTILITY_NAMES if x not in recent_utility), UTILITY_NAMES[hash(workspace + "util") % len(UTILITY_NAMES)])

    # 4–6 位小写字母前缀：全项目 Dart 类名/文件名/顶层标识（与 batch Phase 2 约定一致）
    def _pick_dart_prefix():
        rnd = random.Random(hash(workspace) ^ int(datetime.now().strftime("%Y%m%d")))
        for length in (5, 4, 6):
            for _ in range(400):
                p = "".join(rnd.choice(string.ascii_lowercase) for _ in range(length))
                if p not in recent_dart_prefix:
                    return p
        return "app" + "".join(rnd.choice(string.ascii_lowercase) for _ in range(2))

    out_file_existing = os.path.join(workspace, "本包代码组合.json")
    preserved_prefix = None
    if os.path.isfile(out_file_existing):
        try:
            with open(out_file_existing, "r", encoding="utf-8") as f:
                old_combo = json.load(f)
            preserved_prefix = (old_combo.get("dartCodePrefix") or "").strip().lower()
            if preserved_prefix and 4 <= len(preserved_prefix) <= 6 and preserved_prefix.isalpha():
                pass  # keep
            else:
                preserved_prefix = None
        except Exception:
            preserved_prefix = None

    dart_code_prefix = preserved_prefix or _pick_dart_prefix()

    out = {
        "dartCodePrefix": dart_code_prefix,
        "namingStyle": chosen[0],
        "folderStyle": chosen[1],
        "architecture": chosen[2],
        "stateManagement": chosen[3],
        "codeOrganization": chosen[4],
        "fileNaming": file_naming,
        "importStyle": import_style,
        "constantsLayout": constants_layout,
        "iapModuleName": iap_name,
        "reportModuleName": report_name,
        "constantsModuleName": const_name,
        "networkLayerName": network_name,
        "routeCoordinatorName": router_name,
        "utilityHelperName": utility_name,
    }

    out_file = os.path.join(workspace, "本包代码组合.json")
    os.makedirs(os.path.dirname(out_file) or ".", exist_ok=True)
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)
    print(out_file)

if __name__ == "__main__":
    main()
