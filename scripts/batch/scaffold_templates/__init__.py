"""Scaffold template constants and generators for dimension-locked Flutter packages."""

from __future__ import annotations

# Shared feature dependencies (Agent may rely on these being present).
FEATURE_DEPENDENCIES: dict[str, str] = {
    "in_app_purchase": "^3.2.0",
    "image_picker": "^1.1.2",
    "record": "^5.1.2",
    "gal": "^2.3.0",
    "shared_preferences": "^2.3.3",
    "path_provider": "^2.1.4",
    "google_fonts": "^6.2.1",
    "permission_handler": "^11.3.1",
    "webview_flutter": "^4.10.0",
    "webview_flutter_wkwebview": "^3.16.0",
    "shimmer": "^3.0.0",
    "flutter_animate": "^4.5.0",
    "video_player": "^2.9.2",
}

STATE_DEPENDENCIES: dict[str, dict[str, str]] = {
    "getx": {"get": "^4.6.6"},
    "setstate": {},
    "bloc": {"flutter_bloc": "^8.1.6"},
    "provider": {"provider": "^6.1.2"},
    "mobx": {"flutter_mobx": "^2.2.1", "mobx": "^2.3.3"},
    "redux": {"flutter_redux": "^0.10.0", "redux": "^5.0.0"},
}

STATE_DEV_DEPENDENCIES: dict[str, dict[str, str]] = {
    "mobx": {"build_runner": "^2.4.13", "mobx_codegen": "^2.6.1"},
}

FORBIDDEN_STATE_IMPORTS: dict[str, tuple[str, ...]] = {
    "setstate": (
        "package:provider/",
        "package:flutter_bloc/",
        "package:get/",
        "package:flutter_mobx/",
        "package:mobx/",
        "package:flutter_redux/",
        "package:redux/",
        "extends ChangeNotifier",
        "Provider.of<",
        "Consumer<",
        "BlocBuilder<",
        "BlocProvider",
        "MultiBlocProvider",
        "Obx(",
        "GetMaterialApp",
        "StoreProvider",
        "StoreConnector",
    ),
    "getx": (
        "package:provider/",
        "package:flutter_bloc/",
        "package:flutter_mobx/",
        "package:flutter_redux/",
        "BlocBuilder<",
        "BlocProvider",
        "MultiBlocProvider",
        "Provider.of<",
        "StoreProvider",
    ),
    "bloc": (
        "package:provider/",
        "package:get/",
        "package:flutter_mobx/",
        "package:flutter_redux/",
        "Obx(",
        "GetMaterialApp",
        "Provider.of<",
        "StoreProvider",
    ),
    "provider": (
        "package:flutter_bloc/",
        "package:get/",
        "package:flutter_mobx/",
        "package:flutter_redux/",
        "Obx(",
        "GetMaterialApp",
        "BlocBuilder<",
        "StoreProvider",
    ),
    "mobx": (
        "package:provider/",
        "package:flutter_bloc/",
        "package:get/",
        "package:flutter_redux/",
        "Obx(",
        "GetMaterialApp",
        "BlocBuilder<",
        "StoreProvider",
    ),
    "redux": (
        "package:provider/",
        "package:flutter_bloc/",
        "package:get/",
        "package:flutter_mobx/",
        "Obx(",
        "GetMaterialApp",
        "BlocBuilder<",
        "Provider.of<",
    ),
}

STATE_REQUIRED_MARKERS: dict[str, tuple[str, ...]] = {
    "getx": ("package:get/", "GetMaterialApp"),
    "setstate": (),
    "bloc": ("package:flutter_bloc/", "BlocProvider"),
    "provider": ("package:provider/", "MultiProvider"),
    "mobx": ("package:flutter_mobx/", "Observer"),
    "redux": ("package:flutter_redux/", "StoreProvider"),
}

PATTERN_ROLE_DIRS: dict[str, tuple[str, ...]] = {
    "mvc": ("models", "views", "controllers"),
    "mvp": ("models", "views", "presenters"),
    "mvvm": ("models", "views", "viewmodels"),
    "viper": ("views", "interactors", "presenters", "entities", "routers"),
    "simple_mv": ("models", "views"),
}

PATTERN_FORBIDDEN_DIRS: dict[str, tuple[str, ...]] = {
    "simple_mv": ("viewmodels", "presenters", "controllers"),
    "mvc": (),
    "mvp": (),
    "mvvm": (),
    "viper": (),
}

PATTERN_ROLE_STUBS: dict[str, dict[str, str]] = {
    "mvc": {"controllers": "Controller"},
    "mvp": {"presenters": "Presenter"},
    "mvvm": {"viewmodels": "ViewModel"},
    "viper": {
        "interactors": "Interactor",
        "presenters": "Presenter",
        "entities": "Entity",
        "routers": "Router",
    },
    "simple_mv": {},
}

THEME_SUBDIRS: tuple[str, ...] = ("skin", "open_flow")


def prefix_pascal(prefix: str) -> str:
    p = (prefix or "").strip()
    if not p:
        return "App"
    return p[0].upper() + p[1:]


def lib_root_segment(prefix: str, dart_pkg: str) -> str:
    return f"{prefix}_{dart_pkg}"


def role_dir_name(prefix: str, role: str) -> str:
    return f"{prefix}_{role}"


def generate_main_dart(prefix: str, dart_pkg: str) -> str:
    seg = lib_root_segment(prefix, dart_pkg)
    pascal = prefix_pascal(prefix)
    return f"""import 'package:flutter/material.dart';
import 'package:flutter/services.dart';

import '{seg}/{prefix}_app.dart';

void main() {{
  WidgetsFlutterBinding.ensureInitialized();
  SystemChrome.setPreferredOrientations([
    DeviceOrientation.portraitUp,
  ]);
  runApp(const {pascal}App());
}}
"""


def generate_app_dart(
    prefix: str,
    dart_pkg: str,
    state_key: str,
    *,
    home_import: str | None = None,
    skin_bucket: str | None = None,
) -> str:
    pascal = prefix_pascal(prefix)
    seg = lib_root_segment(prefix, dart_pkg)
    bucket = skin_bucket or f"{prefix}_skin"
    if home_import is None:
        home_import = f"{seg}/{bucket}/{prefix}_home_placeholder.dart"
    home_widget = f"{pascal}HomePlaceholder"
    skin_import = f"{seg}/{bucket}/{prefix}_palette_tokens.dart"
    bg_import = f"{seg}/{bucket}/{prefix}_global_background.dart"
    home_with_bg = (
        f"const {pascal}GlobalBackground(child: {home_widget}())"
    )

    if state_key == "getx":
        return f"""import 'package:flutter/material.dart';
import 'package:get/get.dart';

import '{home_import}';
import '{skin_import}';
import '{bg_import}';

/// Dimension-locked root app widget (GetX). Do NOT replace GetMaterialApp.
class {pascal}App extends StatelessWidget {{
  const {pascal}App({{super.key}});

  @override
  Widget build(BuildContext context) {{
    return GetMaterialApp(
      title: '{pascal}',
      theme: {pascal}AppTheme.light,
      darkTheme: {pascal}AppTheme.dark,
      themeMode: ThemeMode.system,
      home: {home_with_bg},
    );
  }}
}}
"""
    if state_key == "bloc":
        return f"""import 'package:flutter/material.dart';
import 'package:flutter_bloc/flutter_bloc.dart';

import '{home_import}';
import '{skin_import}';
import '{bg_import}';

/// Dimension-locked root app widget (Bloc). Keep MultiBlocProvider at root.
class {pascal}App extends StatelessWidget {{
  const {pascal}App({{super.key}});

  @override
  Widget build(BuildContext context) {{
    return MultiBlocProvider(
      providers: const [],
      child: MaterialApp(
        title: '{pascal}',
        theme: {pascal}AppTheme.light,
        darkTheme: {pascal}AppTheme.dark,
        themeMode: ThemeMode.system,
        home: {home_with_bg},
      ),
    );
  }}
}}
"""
    if state_key == "provider":
        return f"""import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '{home_import}';
import '{skin_import}';
import '{bg_import}';

/// Dimension-locked root app widget (Provider). Keep MultiProvider at root.
class {pascal}App extends StatelessWidget {{
  const {pascal}App({{super.key}});

  @override
  Widget build(BuildContext context) {{
    return MultiProvider(
      providers: const [],
      child: MaterialApp(
        title: '{pascal}',
        theme: {pascal}AppTheme.light,
        darkTheme: {pascal}AppTheme.dark,
        themeMode: ThemeMode.system,
        home: {home_with_bg},
      ),
    );
  }}
}}
"""
    if state_key == "mobx":
        return f"""import 'package:flutter/material.dart';
import 'package:flutter_mobx/flutter_mobx.dart';

import '{home_import}';
import '{skin_import}';
import '{bg_import}';

/// Dimension-locked root app widget (MobX). Use Observer for reactive UI.
class {pascal}App extends StatelessWidget {{
  const {pascal}App({{super.key}});

  @override
  Widget build(BuildContext context) {{
    return MaterialApp(
      title: '{pascal}',
      theme: {pascal}AppTheme.light,
      darkTheme: {pascal}AppTheme.dark,
      themeMode: ThemeMode.system,
      home: Observer(
        builder: (_) => {home_with_bg},
      ),
    );
  }}
}}
"""
    if state_key == "redux":
        return f"""import 'package:flutter/material.dart';
import 'package:flutter_redux/flutter_redux.dart';
import 'package:redux/redux.dart';

import '{home_import}';
import '{skin_import}';
import '{bg_import}';

/// Dimension-locked root app widget (Redux). Keep StoreProvider at root.
class {pascal}App extends StatelessWidget {{
  const {pascal}App({{super.key}});

  static final Store<dynamic> _store = Store<dynamic>(
    (state, action) => state,
    initialState: null,
  );

  @override
  Widget build(BuildContext context) {{
    return StoreProvider<dynamic>(
      store: _store,
      child: MaterialApp(
        title: '{pascal}',
        theme: {pascal}AppTheme.light,
        darkTheme: {pascal}AppTheme.dark,
        themeMode: ThemeMode.system,
        home: {home_with_bg},
      ),
    );
  }}
}}
"""
    return f"""import 'package:flutter/material.dart';

import '{home_import}';
import '{skin_import}';
import '{bg_import}';

/// Dimension-locked root app widget (SetState). Use StatefulWidget + setState only.
class {pascal}App extends StatefulWidget {{
  const {pascal}App({{super.key}});

  @override
  State<{pascal}App> createState() => _{pascal}AppState();
}}

class _{pascal}AppState extends State<{pascal}App> {{
  @override
  Widget build(BuildContext context) {{
    return MaterialApp(
      title: '{pascal}',
      theme: {pascal}AppTheme.light,
      darkTheme: {pascal}AppTheme.dark,
      themeMode: ThemeMode.system,
      home: {home_with_bg},
    );
  }}
}}
"""


def generate_home_placeholder(prefix: str) -> str:
    pascal = prefix_pascal(prefix)
    return f"""import 'package:flutter/material.dart';

/// Scaffold placeholder — replace body inside region:business-impl only.
/// Parent ({pascal}GlobalBackground) already paints ColoredBox(surface) underneath,
/// so this Scaffold may stay transparent without risking a black screen.
class {pascal}HomePlaceholder extends StatelessWidget {{
  const {pascal}HomePlaceholder({{super.key}});

  @override
  Widget build(BuildContext context) {{
    // region: business-impl
    return const Scaffold(
      backgroundColor: Colors.transparent,
      body: Center(child: Text('Implement app shell here')),
    );
    // endregion
  }}
}}
"""


def generate_role_stub(prefix: str, role: str, suffix: str) -> str:
    pascal = prefix_pascal(prefix)
    class_name = f"{pascal}Base{suffix}"
    return f"""/// Architecture role stub ({suffix}). Extend in business-impl region.
abstract class {class_name} {{
  // region: business-impl
  // Add role methods here.
  // endregion
}}
"""


def generate_model_stub(prefix: str) -> str:
    pascal = prefix_pascal(prefix)
    return f"""/// Base model stub for {pascal} architecture layer.
abstract class {pascal}BaseModel {{
  // region: business-impl
  // endregion
}}
"""


def expected_scaffold_paths(
    prefix: str,
    dart_pkg: str,
    pattern_key: str,
    folder_map: dict[str, dict[str, str]] | None = None,
    *,
    lib_layout: str = "flat_skin_role",
    skin_bucket: str | None = None,
) -> list[str]:
    """Relative paths under Flutter project root."""
    seg = lib_root_segment(prefix, dart_pkg)
    bucket = skin_bucket or f"{prefix}_skin"
    paths = [
        "lib/main.dart",
        f"lib/{seg}/{prefix}_app.dart",
    ]

    def _skin_paths(bucket_name: str) -> None:
        paths.extend(
            [
                f"lib/{seg}/{bucket_name}/{prefix}_palette_tokens.dart",
                f"lib/{seg}/{bucket_name}/{prefix}_global_background.dart",
                f"lib/{seg}/{bucket_name}/{prefix}_image_box.dart",
            ]
        )

    if lib_layout == "dual_hub":
        _skin_paths(f"{prefix}_core")
    elif lib_layout == "single_lane":
        _skin_paths(bucket)
        paths.append(f"lib/{seg}/{prefix}_lane/{prefix}_home_placeholder.dart")
        roles = PATTERN_ROLE_DIRS.get(pattern_key, ())
        for role in roles:
            entry = (folder_map or {}).get(role, {})
            stub_name = entry.get("stubBasename") or f"{prefix}_{role}_anchor"
            if role == "models" or role in PATTERN_ROLE_STUBS.get(pattern_key, {}):
                paths.append(f"lib/{seg}/{prefix}_lane/{stub_name}.dart")
        return paths
    else:
        _skin_paths(bucket)

    if lib_layout == "flat_skin_role_helper":
        paths.append(f"lib/{seg}/{prefix}_helper/.gitkeep")

    roles = PATTERN_ROLE_DIRS.get(pattern_key, ())
    core_roles = frozenset({"models", "entities"})

    for role in roles:
        entry = (folder_map or {}).get(role, {})
        folder_basename = entry.get("folderBasename") or f"{prefix}_{role}"
        if lib_layout == "dual_hub":
            hub = f"{prefix}_core" if role in core_roles else f"{prefix}_surface"
            role_prefix = f"lib/{seg}/{hub}/{folder_basename}"
        else:
            role_prefix = f"lib/{seg}/{folder_basename}"

        if role == "views":
            if lib_layout == "shell_bay":
                paths.append(
                    f"{role_prefix}/{prefix}_bay/{prefix}_home_placeholder.dart"
                )
            else:
                paths.append(f"{role_prefix}/{prefix}_home_placeholder.dart")

        stub_name = entry.get("stubBasename") or f"{prefix}_{role}_anchor"
        if role == "models" or role in PATTERN_ROLE_STUBS.get(pattern_key, {}):
            paths.append(f"{role_prefix}/{stub_name}.dart")
        else:
            paths.append(f"{role_prefix}/.gitkeep")

        if lib_layout in ("nested_role_leaf", "shell_bay", "feature_mod_wrap"):
            from batch.programming_layout import role_implementation_subdir

            sub = role_implementation_subdir(prefix, role, lib_layout)
            if sub:
                paths.append(f"{role_prefix}/{sub}/.gitkeep")

    return paths


def generate_flow_stub(prefix: str) -> str:
    pascal = prefix_pascal(prefix)
    return f"""/// Open-flow theme stub — fill business logic in region only.
class {pascal}FlowStub {{
  // region: business-impl
  // endregion
}}
"""


def generate_palette_tokens(prefix: str) -> str:
    """Pre-built design tokens + light/dark ThemeData with safe input contrast."""
    pascal = prefix_pascal(prefix)
    return f"""import 'package:flutter/material.dart';

/// Pre-built palette tokens for {pascal}. DO NOT rewrite this file.
/// Agent may ADD new tokens or theme extensions, but light/dark ThemeData,
/// AppColors basics, and inputDecorationTheme are LOCKED to avoid the common
/// pitfalls: invisible light-mode TextField, dark grey on dark bg, missing
/// inputDecorationTheme. Extend via separate files when needed.
class {pascal}Palette {{
  {pascal}Palette._();

  // Brand seed (Agent may tune, keep within warm pastel range).
  static const Color primary = Color(0xFF6E55C7);
  static const Color secondary = Color(0xFFE4A1B9);
  static const Color accent = Color(0xFFF5C97B);

  // Light surfaces and text.
  static const Color surface = Color(0xFFFFFFFF);
  static const Color background = Color(0xFFFAF6F0);
  static const Color outline = Color(0xFFE0DAD0);
  static const Color textPrimary = Color(0xFF2D2D2D);
  static const Color textSecondary = Color(0xFF6B6B6B);
  static const Color textTertiary = Color(0xFF9A9A9A);

  // Dark surfaces and text.
  static const Color surfaceDark = Color(0xFF1E1E1E);
  static const Color cardDark = Color(0xFF252525);
  static const Color backgroundDark = Color(0xFF121212);
  static const Color outlineDark = Color(0xFF3A3A3A);
  static const Color textPrimaryDark = Color(0xFFE8E8E8);
  static const Color textSecondaryDark = Color(0xFFB0B0B0);
  static const Color textTertiaryDark = Color(0xFF7A7A7A);

  static Color textPrimaryFor({{required bool isDark}}) =>
      isDark ? textPrimaryDark : textPrimary;
  static Color textSecondaryFor({{required bool isDark}}) =>
      isDark ? textSecondaryDark : textSecondary;
  static Color surfaceFor({{required bool isDark}}) =>
      isDark ? surfaceDark : surface;
  static Color backgroundFor({{required bool isDark}}) =>
      isDark ? backgroundDark : background;
}}

/// LOCKED ThemeData factory. Agent must use these getters in MaterialApp.
class {pascal}AppTheme {{
  {pascal}AppTheme._();

  static ThemeData get light => _build(isDark: false);
  static ThemeData get dark => _build(isDark: true);

  static ThemeData _build({{required bool isDark}}) {{
    final scheme = ColorScheme.fromSeed(
      seedColor: {pascal}Palette.primary,
      brightness: isDark ? Brightness.dark : Brightness.light,
      surface: {pascal}Palette.surfaceFor(isDark: isDark),
    );
    final textPrimary = {pascal}Palette.textPrimaryFor(isDark: isDark);
    final textSecondary = {pascal}Palette.textSecondaryFor(isDark: isDark);
    final surface = {pascal}Palette.surfaceFor(isDark: isDark);
    final background = {pascal}Palette.backgroundFor(isDark: isDark);
    return ThemeData(
      useMaterial3: true,
      colorScheme: scheme,
      brightness: isDark ? Brightness.dark : Brightness.light,
      scaffoldBackgroundColor: background,
      canvasColor: surface,
      cardColor: isDark ? {pascal}Palette.cardDark : surface,
      dividerColor: isDark
          ? {pascal}Palette.outlineDark
          : {pascal}Palette.outline,
      appBarTheme: AppBarTheme(
        backgroundColor: surface,
        foregroundColor: textPrimary,
        surfaceTintColor: Colors.transparent,
        elevation: 0,
        titleTextStyle: TextStyle(
          color: textPrimary,
          fontSize: 18,
          fontWeight: FontWeight.w600,
        ),
      ),
      textTheme: TextTheme(
        headlineLarge: TextStyle(
          fontSize: 28,
          fontWeight: FontWeight.w600,
          color: textPrimary,
        ),
        titleLarge: TextStyle(
          fontSize: 20,
          fontWeight: FontWeight.w600,
          color: textPrimary,
        ),
        bodyLarge: TextStyle(fontSize: 16, color: textPrimary, height: 1.5),
        bodyMedium: TextStyle(fontSize: 14, color: textPrimary, height: 1.4),
        bodySmall: TextStyle(fontSize: 12, color: textSecondary, height: 1.4),
        labelSmall: TextStyle(fontSize: 11, color: textSecondary),
      ),
      inputDecorationTheme: InputDecorationTheme(
        filled: true,
        fillColor: surface,
        hintStyle: TextStyle(color: textSecondary, fontSize: 14),
        labelStyle: TextStyle(color: textSecondary, fontSize: 13),
        helperStyle: TextStyle(color: textSecondary, fontSize: 12),
        prefixIconColor: textSecondary,
        suffixIconColor: textSecondary,
        contentPadding: const EdgeInsets.symmetric(
          horizontal: 14,
          vertical: 12,
        ),
        border: OutlineInputBorder(
          borderRadius: BorderRadius.circular(12),
          borderSide: BorderSide(
            color: isDark ? {pascal}Palette.outlineDark : {pascal}Palette.outline,
          ),
        ),
        enabledBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(12),
          borderSide: BorderSide(
            color: isDark ? {pascal}Palette.outlineDark : {pascal}Palette.outline,
          ),
        ),
        focusedBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(12),
          borderSide: BorderSide(color: {pascal}Palette.primary, width: 1.5),
        ),
      ),
      bottomNavigationBarTheme: BottomNavigationBarThemeData(
        backgroundColor: surface,
        selectedItemColor: {pascal}Palette.primary,
        unselectedItemColor: textSecondary,
        type: BottomNavigationBarType.fixed,
        showUnselectedLabels: true,
      ),
      elevatedButtonTheme: ElevatedButtonThemeData(
        style: ElevatedButton.styleFrom(
          backgroundColor: {pascal}Palette.primary,
          foregroundColor: Colors.white,
          shape: RoundedRectangleBorder(
            borderRadius: BorderRadius.circular(14),
          ),
          padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 14),
        ),
      ),
    );
  }}
}}
"""


def generate_global_background(prefix: str) -> str:
    """Root Stack: ColoredBox(surface) -> child (no mandatory background image)."""
    pascal = prefix_pascal(prefix)
    return f"""import 'package:flutter/material.dart';

/// LOCKED root background. Use {pascal}GlobalBackground(child: Scaffold(...))
/// at the app shell ONCE; never wrap individual tabs.
class {pascal}GlobalBackground extends StatelessWidget {{
  const {pascal}GlobalBackground({{
    super.key,
    required this.child,
  }});

  final Widget child;

  @override
  Widget build(BuildContext context) {{
    final surface = Theme.of(context).colorScheme.surface;
    return Stack(
      fit: StackFit.expand,
      children: [
        ColoredBox(color: surface),
        child,
      ],
    );
  }}
}}
"""


def generate_image_box(prefix: str) -> str:
    """Image.asset wrapper that always shows a themed fallback on error."""
    pascal = prefix_pascal(prefix)
    return f"""import 'package:flutter/material.dart';

/// Always-safe Image.asset wrapper.
/// Use {pascal}ImageBox.asset(path) instead of raw Image.asset to guarantee:
/// 1) errorBuilder returns a themed ColoredBox (never blank/black).
/// 2) Optional frameBuilder fade-in for smoother first paint.
class {pascal}ImageBox extends StatelessWidget {{
  const {pascal}ImageBox.asset(
    this.assetPath, {{
    super.key,
    this.fit = BoxFit.cover,
    this.width,
    this.height,
    this.opacity,
    this.fallbackColor,
    this.fallbackIcon = Icons.image_outlined,
  }});

  final String assetPath;
  final BoxFit fit;
  final double? width;
  final double? height;
  final double? opacity;
  final Color? fallbackColor;
  final IconData fallbackIcon;

  @override
  Widget build(BuildContext context) {{
    final scheme = Theme.of(context).colorScheme;
    final fill = fallbackColor ?? scheme.primary.withOpacity(0.08);
    return Image.asset(
      assetPath,
      fit: fit,
      width: width,
      height: height,
      opacity: opacity != null ? AlwaysStoppedAnimation(opacity!) : null,
      frameBuilder: (context, child, frame, wasSync) {{
        if (wasSync || frame != null) return child;
        return ColoredBox(color: fill);
      }},
      errorBuilder: (context, error, stack) => Container(
        color: fill,
        alignment: Alignment.center,
        child: Icon(
          fallbackIcon,
          color: scheme.primary.withOpacity(0.45),
          size: 32,
        ),
      ),
    );
  }}
}}
"""
