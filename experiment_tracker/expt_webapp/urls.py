from django.urls import path, include
from rest_framework.routers import DefaultRouter

# --- API views (DRF) ---
from .views import (
    ModelViewSet, ExperimentViewSet, RunViewSet,
    SetupViewSet, PlatformViewSet, MaterialViewSet, MaterialTypeViewSet,
    SetupPlatformViewSet, ExperimentMaterialViewSet, ModelMaterialViewSet,
    RunLogViewSet, RunMetricViewSet, RunOutputViewSet,
    ParameterViewSet, TagViewSet, EntityTagViewSet,
    DashboardViewSet, GraphViewSet,
    SearchView, ActivityView, ModelComparisonView, VersionTrackingView,
)

# --- Template views (UI) ---
from .template_views import (
    dashboard,
    model_list, model_detail, model_create, model_edit,
    experiment_list, experiment_detail, experiment_create, experiment_edit,
    run_list, run_detail, run_create, run_edit,
    material_list, material_detail, material_create, material_edit,
    material_type_list, material_type_detail, material_type_create, material_type_edit,
    setup_list, setup_detail, setup_create, setup_edit,
    platform_list, platform_detail, platform_create, platform_edit,
    tag_list, tag_detail, tag_create, tag_edit,
    search,
)

# =============================================================================
# API ROUTER
# =============================================================================

router = DefaultRouter()

# Core entities
router.register(r'models',         ModelViewSet,         basename='model-api')
router.register(r'experiments',    ExperimentViewSet,    basename='experiment-api')
router.register(r'runs',           RunViewSet,           basename='run-api')
router.register(r'setups',         SetupViewSet,         basename='setup-api')
router.register(r'platforms',      PlatformViewSet,      basename='platform-api')
router.register(r'materials',      MaterialViewSet,      basename='material-api')
router.register(r'material-types', MaterialTypeViewSet,  basename='material-type-api')

# Relationship layer
router.register(r'setup-platforms',      SetupPlatformViewSet,      basename='setup-platform-api')
router.register(r'experiment-materials', ExperimentMaterialViewSet, basename='experiment-material-api')
router.register(r'model-materials',      ModelMaterialViewSet,      basename='model-material-api')

# Observability layer
router.register(r'run-logs',    RunLogViewSet,    basename='run-log-api')
router.register(r'run-metrics', RunMetricViewSet, basename='run-metric-api')
router.register(r'run-outputs', RunOutputViewSet, basename='run-output-api')

# Metadata
router.register(r'parameters',  ParameterViewSet,  basename='parameter-api')
router.register(r'tags',        TagViewSet,        basename='tag-api')
router.register(r'entity-tags', EntityTagViewSet,  basename='entity-tag-api')

# Dashboard & graph (no model queryset — basename required)
router.register(r'dashboard', DashboardViewSet, basename='dashboard')
router.register(r'graph',     GraphViewSet,     basename='graph')


# =============================================================================
# URL PATTERNS
# =============================================================================

urlpatterns = [

    # ------------------------------------------------------------------
    # UI — Template Views
    # ------------------------------------------------------------------

    path('', dashboard, name='dashboard'),
    path('search/', search, name='search'),

    # Models
    path('models/',               model_list,   name='model-list'),
    path('models/new/',           model_create, name='model-create'),
    path('models/<int:pk>/',      model_detail, name='model-detail'),
    path('models/<int:pk>/edit/', model_edit,   name='model-edit'),

    # Experiments
    path('experiments/',               experiment_list,   name='experiment-list'),
    path('experiments/new/',           experiment_create, name='experiment-create'),
    path('experiments/<int:pk>/',      experiment_detail, name='experiment-detail'),
    path('experiments/<int:pk>/edit/', experiment_edit,   name='experiment-edit'),

    # Runs
    path('runs/',               run_list,   name='run-list'),
    path('runs/new/',           run_create, name='run-create'),
    path('runs/<int:pk>/',      run_detail, name='run-detail'),
    path('runs/<int:pk>/edit/', run_edit,   name='run-edit'),

    # Material Types
    path('material-types/',               material_type_list,   name='material-type-list'),
    path('material-types/new/',           material_type_create, name='material-type-create'),
    path('material-types/<int:pk>/',      material_type_detail, name='material-type-detail'),
    path('material-types/<int:pk>/edit/', material_type_edit,   name='material-type-edit'),

    # Materials
    path('materials/',               material_list,   name='material-list'),
    path('materials/new/',           material_create, name='material-create'),
    path('materials/<int:pk>/',      material_detail, name='material-detail'),
    path('materials/<int:pk>/edit/', material_edit,   name='material-edit'),

    # Setups
    path('setups/',               setup_list,   name='setup-list'),
    path('setups/new/',           setup_create, name='setup-create'),
    path('setups/<int:pk>/',      setup_detail, name='setup-detail'),
    path('setups/<int:pk>/edit/', setup_edit,   name='setup-edit'),

    # Platforms
    path('platforms/',               platform_list,   name='platform-list'),
    path('platforms/new/',           platform_create, name='platform-create'),
    path('platforms/<int:pk>/',      platform_detail, name='platform-detail'),
    path('platforms/<int:pk>/edit/', platform_edit,   name='platform-edit'),

    # Tags
    path('tags/',               tag_list,   name='tag-list'),
    path('tags/new/',           tag_create, name='tag-create'),
    path('tags/<int:pk>/',      tag_detail, name='tag-detail'),
    path('tags/<int:pk>/edit/', tag_edit,   name='tag-edit'),

    # ------------------------------------------------------------------
    # REST API — DRF ViewSets
    # ------------------------------------------------------------------

    path('api/', include(router.urls)),

    # Standalone API views
    path('api/search/',          SearchView.as_view(),          name='api-search'),
    path('api/activity/',        ActivityView.as_view(),        name='api-activity'),
    path('api/compare/models/',  ModelComparisonView.as_view(), name='api-compare-models'),
    path('api/versions/',        VersionTrackingView.as_view(), name='api-version-tracking'),
]


# =============================================================================
# UI ROUTE REFERENCE
# =============================================================================
#
#  GET  /                          → Dashboard
#  GET  /search/?q=...             → Search
#
#  GET  /models/                   → Model list
#  GET  /models/new/               → Create model form
#  GET  /models/{id}/              → Model detail
#  GET  /models/{id}/edit/         → Edit model form
#
#  GET  /experiments/              → Experiment list
#  GET  /experiments/new/          → Create experiment form
#  GET  /experiments/{id}/         → Experiment detail
#  GET  /experiments/{id}/edit/    → Edit experiment form
#
#  GET  /runs/                     → Run list
#  GET  /runs/new/                 → Create run form
#  GET  /runs/{id}/                → Run detail (metrics/logs/outputs/timeline)
#  GET  /runs/{id}/edit/           → Edit run form
#
#  GET  /materials/                → Material list
#  GET  /materials/new/            → Create material form
#  GET  /materials/{id}/           → Material detail
#  GET  /materials/{id}/edit/      → Edit material form
#
#  GET  /setups/                   → Setup list
#  GET  /setups/new/               → Create setup form
#  GET  /setups/{id}/              → Setup detail
#  GET  /setups/{id}/edit/         → Edit setup form
#
#  GET  /platforms/                → Platform list
#  GET  /platforms/new/            → Create platform form
#  GET  /platforms/{id}/           → Platform detail
#  GET  /platforms/{id}/edit/      → Edit platform form
#
#  GET  /tags/                     → Tag list
#  GET  /tags/new/                 → Create tag form
#  GET  /tags/{id}/                → Tag detail
#  GET  /tags/{id}/edit/           → Edit tag form
#
# =============================================================================
# API ROUTE REFERENCE
# =============================================================================
#
#  GET/POST             /api/models/
#  GET/PATCH/DELETE     /api/models/{id}/
#  GET                  /api/models/{id}/experiments/
#  GET                  /api/models/{id}/lineage/
#  GET                  /api/models/{id}/materials/
#  GET                  /api/models/{id}/stats/
#
#  GET/POST             /api/experiments/
#  GET/PATCH/DELETE     /api/experiments/{id}/
#  GET                  /api/experiments/{id}/runs/
#  GET                  /api/experiments/{id}/summary/
#  GET                  /api/experiments/{id}/materials/
#
#  GET/POST             /api/runs/
#  GET/PATCH/DELETE     /api/runs/{id}/
#  GET                  /api/runs/{id}/logs/
#  GET                  /api/runs/{id}/metrics/
#  GET                  /api/runs/{id}/outputs/
#  GET                  /api/runs/{id}/timeline/
#  GET                  /api/runs/{id}/summary/
#  POST                 /api/runs/compare_metrics/
#
#  GET                  /api/dashboard/global_overview/
#  GET                  /api/dashboard/model/?model_id=X
#  GET                  /api/dashboard/experiment/?experiment_id=X
#  GET                  /api/dashboard/run/?run_id=X
#
#  GET                  /api/graph/model/?model_id=X
#  GET                  /api/graph/experiment/?experiment_id=X
#
#  GET                  /api/search/?q=...
#  GET                  /api/activity/
#  POST                 /api/compare/models/
#  GET                  /api/versions/?entity=model&name=X