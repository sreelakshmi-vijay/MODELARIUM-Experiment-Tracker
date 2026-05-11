from django.shortcuts import render
from django.db.models import Count, Avg, Q, Max, Min
from django.utils import timezone
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework import serializers
 
from .models import (
    Model, Experiment, Run, Setup, Platform,
    SetupPlatform, ExperimentMaterial, ModelMaterial,
    MaterialType, Material, Parameter, RunMetric,
    RunOutput, RunLog, Tag, EntityTag,
)

# =============================================================================
# DJANGO REST API VIEW ARCHITECTURE FOR THIS PROJECT
# =============================================================================


# -----------------------------------------------------------------------------
# BIG PICTURE: WHAT THE VIEW LAYER SUPPORTS
# -----------------------------------------------------------------------------
#
# This system is designed around five major interaction layers:
#
# A. CORE HIERARCHY NAVIGATION
#    Model → Experiment → Run → Outputs / Logs / Metrics
#
# B. ASSET SYSTEM
#    Materials and MaterialTypes
#    Used by Models and Experiments
#
# C. EXECUTION SYSTEM
#    Runs execute experiments using Setups on Platforms
#
# D. METADATA SYSTEM
#    Parameters provide flexible key-value metadata
#    Tags provide cross-entity labeling
#
# E. OBSERVABILITY LAYER
#    RunLogs, RunMetrics, RunOutputs capture runtime behavior
#
# The view layer supports:
#    - Full CRUD across all entities
#    - Deep hierarchical navigation across relationships
#    - Cross-entity filtering and lookup
#    - Aggregation and analytics dashboards
#    - Relationship graph traversal


# The API layer uses Django REST Framework with:
#
#   - ViewSets as the primary interface
#   - Nested routing for hierarchical navigation
#   - Custom actions for domain-specific operations
#   - Aggregation endpoints for analytics and reporting


# -----------------------------------------------------------------------------
# CORE VIEWSETS
# -----------------------------------------------------------------------------


# -----------------------------------------------------------------------------
# MODEL VIEWSET (CENTRAL ENTITY)
# -----------------------------------------------------------------------------
#
# ModelViewSet manages ML models and their lifecycle.
#
# It supports:
#   - CRUD operations for models
#   - Listing experiments under a model
#   - Traversing model lineage through parent relationships
#   - Retrieving materials linked to models
#   - Computing aggregated model statistics such as:
#       * total experiments
#       * total runs
#       * success rate

# -----------------------------------------------------------------------------
# EXPERIMENT VIEWSET
# -----------------------------------------------------------------------------
#
# ExperimentViewSet manages experiment definitions tied to models.
#
# It supports:
#   - CRUD operations for experiments
#   - Listing runs under an experiment
#   - Generating experiment summaries
#   - Linking experiments back to models
#   - Aggregating run-level performance metrics


# -----------------------------------------------------------------------------
# RUN VIEWSET (MOST CRITICAL EXECUTION ENTITY)
# -----------------------------------------------------------------------------
#
# RunViewSet manages execution instances of experiments.
#
# It supports:
#   - CRUD operations for runs
#   - Retrieving and filtering logs
#   - Retrieving and comparing metrics across runs
#   - Managing outputs such as files, artifacts, and results
#   - Reconstructing execution timelines
#   - Generating run summaries with aggregated insights


# -----------------------------------------------------------------------------
# SETUP VIEWSET
# -----------------------------------------------------------------------------
#
# SetupViewSet manages execution environments.
#
# It supports:
#   - CRUD operations for setups
#   - Linking setups with platforms
#   - Listing runs executed under a setup
#   - Merging platform configurations into a unified setup config


# -----------------------------------------------------------------------------
# PLATFORM VIEWSET
# -----------------------------------------------------------------------------
#
# PlatformViewSet manages compute and runtime platforms.
#
# It supports:
#   - CRUD operations for platforms
#   - Linking platforms to setups
#   - Tracking platform usage across runs


# -----------------------------------------------------------------------------
# MATERIAL VIEWSET
# -----------------------------------------------------------------------------
#
# MaterialViewSet manages versioned assets such as datasets and scripts.
#
# It supports:
#   - CRUD operations for materials
#   - Linking materials to models and experiments
#   - Tracking material usage across the system
#   - Exploring dependencies between materials


# -----------------------------------------------------------------------------
# MATERIAL TYPE VIEWSET
# -----------------------------------------------------------------------------
#
# MaterialTypeViewSet manages categories of materials.
#
# It supports:
#   - CRUD operations for material types
#   - Listing materials under each type


# -----------------------------------------------------------------------------
# PARAMETER SYSTEM (FLEXIBLE METADATA LAYER)
# -----------------------------------------------------------------------------
#
# ParameterViewSet manages polymorphic metadata across all entities.
#
# It supports:
#   - Listing parameters by entity type and entity ID
#   - Creating and updating parameters
#   - Bulk parameter updates
#   - Searching parameters across entities
#   - Aggregating metadata per entity


# -----------------------------------------------------------------------------
# TAGGING SYSTEM (CROSS-CUTTING LABELS)
# -----------------------------------------------------------------------------
#
# TagViewSet manages reusable tags.
#
# It supports:
#   - Creating and managing tags
#   - Assigning tags to entities
#   - Removing tags from entities
#   - Retrieving entities by tag
#   - Retrieving tags for an entity


# -----------------------------------------------------------------------------
# OBSERVABILITY LAYER
# -----------------------------------------------------------------------------


# RUN LOGS
# -----------------------------------------------------------------------------
#
# RunLogViewSet manages execution logs.
#
# It supports:
#   - Retrieving logs for a run
#   - Filtering logs by severity level
#   - Filtering logs by time range
#   - Streaming logs for real-time monitoring


# RUN METRICS
# -----------------------------------------------------------------------------
#
# RunMetricViewSet manages performance metrics.
#
# It supports:
#   - Retrieving metrics for a run
#   - Comparing metrics across multiple runs
#   - Aggregating metrics at experiment level


# RUN OUTPUTS
# -----------------------------------------------------------------------------
#
# RunOutputViewSet manages artifacts generated by runs.
#
# It supports:
#   - Listing outputs for a run
#   - Downloading artifacts
#   - Tracking structured results


# -----------------------------------------------------------------------------
# DASHBOARD / ANALYTICS LAYER
# -----------------------------------------------------------------------------
#
# Global Dashboard:
#   - Provides system-wide overview including:
#       * total models
#       * total experiments
#       * total runs
#       * success rate
#       * active runs
#       * failed runs
#
# Model Dashboard:
#   - Provides model-level analytics including:
#       * experiment counts
#       * run success rate
#       * performance trends
#
# Experiment Dashboard:
#   - Provides experiment-level analytics including:
#       * run trends over time
#       * best and worst runs
#       * metric evolution
#
# Run Analytics Dashboard:
#   - Provides execution-level insights including:
#       * runtime breakdown
#       * log distribution
#       * metric progression


# -----------------------------------------------------------------------------
# SEARCH & FILTERING SYSTEM
# -----------------------------------------------------------------------------
#
# Search system supports querying across:
#   - Models
#   - Experiments
#   - Runs
#   - Materials
#   - Tags
#
# Filtering supports:
#   - Status-based filtering
#   - Version-based filtering
#   - Setup-based filtering
#   - Material type filtering


# -----------------------------------------------------------------------------
# RELATIONSHIP GRAPH SYSTEM
# -----------------------------------------------------------------------------
#
# Model Graph:
#   - Shows model lineage
#   - Shows related experiments
#   - Shows linked materials
#
# Experiment Graph:
#   - Shows runs under experiment
#   - Shows setups used
#   - Shows platform distribution


# -----------------------------------------------------------------------------
# ACTIVITY & SYSTEM INSIGHTS
# -----------------------------------------------------------------------------
#
# Activity feed provides:
#   - Latest models created
#   - Latest experiments created
#   - Run failures
#   - System-level events


# -----------------------------------------------------------------------------
# MODEL COMPARISON SYSTEM
# -----------------------------------------------------------------------------
#
# Model comparison supports:
#   - Comparing experiment performance
#   - Comparing run metrics
#   - Comparing material usage patterns


# -----------------------------------------------------------------------------
# VERSION TRACKING SYSTEM
# -----------------------------------------------------------------------------
#
# Version tracking manages:
#   - Model version evolution
#   - Material version evolution


# -----------------------------------------------------------------------------
# MINIMUM REQUIRED VIEWSET STRUCTURE
# -----------------------------------------------------------------------------
#
# CORE ENTITIES:
#   ModelViewSet
#   ExperimentViewSet
#   RunViewSet
#   SetupViewSet
#   PlatformViewSet
#   MaterialViewSet
#   MaterialTypeViewSet
#   TagViewSet
#
# RELATIONSHIP LAYER:
#   SetupPlatformViewSet
#   ExperimentMaterialViewSet
#   ModelMaterialViewSet
#   EntityTagViewSet
#
# OBSERVABILITY LAYER:
#   RunLogViewSet
#   RunMetricViewSet
#   RunOutputViewSet
#
# INFRASTRUCTURE LAYER:
#   ParameterViewSet
#   SearchView
#   DashboardViewSet
#   GraphViewSet


# =============================================================================
# SERIALIZERS
# =============================================================================

class ModelSerializer(serializers.ModelSerializer):
    class Meta:
        model = Model
        fields = '__all__'


class ExperimentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Experiment
        fields = '__all__'


class RunSerializer(serializers.ModelSerializer):
    class Meta:
        model = Run
        fields = '__all__'


class SetupSerializer(serializers.ModelSerializer):
    class Meta:
        model = Setup
        fields = '__all__'


class PlatformSerializer(serializers.ModelSerializer):
    class Meta:
        model = Platform
        fields = '__all__'


class SetupPlatformSerializer(serializers.ModelSerializer):
    class Meta:
        model = SetupPlatform
        fields = '__all__'


class MaterialTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = MaterialType
        fields = '__all__'


class MaterialSerializer(serializers.ModelSerializer):
    class Meta:
        model = Material
        fields = '__all__'


class ExperimentMaterialSerializer(serializers.ModelSerializer):
    class Meta:
        model = ExperimentMaterial
        fields = '__all__'


class ModelMaterialSerializer(serializers.ModelSerializer):
    class Meta:
        model = ModelMaterial
        fields = '__all__'


class ParameterSerializer(serializers.ModelSerializer):
    class Meta:
        model = Parameter
        fields = '__all__'


class RunMetricSerializer(serializers.ModelSerializer):
    class Meta:
        model = RunMetric
        fields = '__all__'


class RunOutputSerializer(serializers.ModelSerializer):
    class Meta:
        model = RunOutput
        fields = '__all__'


class RunLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = RunLog
        fields = '__all__'


class TagSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tag
        fields = '__all__'


class EntityTagSerializer(serializers.ModelSerializer):
    class Meta:
        model = EntityTag
        fields = '__all__'


# =============================================================================
# HELPER
# =============================================================================

def _run_success_rate(runs_qs):
    total = runs_qs.count()
    if total == 0:
        return None
    successful = runs_qs.filter(status='successful').count()
    return round(successful / total * 100, 2)


# =============================================================================
# CORE VIEWSETS
# =============================================================================

# -----------------------------------------------------------------------------
# MODEL VIEWSET
# -----------------------------------------------------------------------------

class ModelViewSet(viewsets.ModelViewSet):
    """
    Full CRUD for ML models plus lineage traversal, linked materials,
    and aggregated statistics.
    """
    queryset = Model.objects.all().order_by('-created_at')
    serializer_class = ModelSerializer

    def get_queryset(self):
        qs = super().get_queryset()
        name = self.request.query_params.get('name')
        version = self.request.query_params.get('version')
        if name:
            qs = qs.filter(name__icontains=name)
        if version:
            qs = qs.filter(version=version)
        return qs

    # GET /models/{id}/experiments/
    @action(detail=True, methods=['get'])
    def experiments(self, request, pk=None):
        model = self.get_object()
        experiments = Experiment.objects.filter(model=model).order_by('-created_at')
        serializer = ExperimentSerializer(experiments, many=True)
        return Response(serializer.data)

    # GET /models/{id}/lineage/
    @action(detail=True, methods=['get'])
    def lineage(self, request, pk=None):
        model = self.get_object()
        ancestors = []
        current = model.parent_model
        while current:
            ancestors.append(ModelSerializer(current).data)
            current = current.parent_model
        children = Model.objects.filter(parent_model=model)
        return Response({
            'model': ModelSerializer(model).data,
            'ancestors': ancestors,
            'children': ModelSerializer(children, many=True).data,
        })

    # GET /models/{id}/materials/
    @action(detail=True, methods=['get'])
    def materials(self, request, pk=None):
        model = self.get_object()
        links = ModelMaterial.objects.filter(model=model).select_related('material')
        data = []
        for link in links:
            entry = MaterialSerializer(link.material).data
            entry['relation_type'] = link.relation_type
            data.append(entry)
        return Response(data)

    # GET /models/{id}/stats/
    @action(detail=True, methods=['get'])
    def stats(self, request, pk=None):
        model = self.get_object()
        experiments = Experiment.objects.filter(model=model)
        runs = Run.objects.filter(experiment__in=experiments)
        return Response({
            'total_experiments': experiments.count(),
            'total_runs': runs.count(),
            'success_rate': _run_success_rate(runs),
            'failed_runs': runs.filter(status='failed').count(),
            'active_runs': runs.filter(status='running').count(),
        })


# -----------------------------------------------------------------------------
# EXPERIMENT VIEWSET
# -----------------------------------------------------------------------------

class ExperimentViewSet(viewsets.ModelViewSet):
    """
    Full CRUD for experiments plus run listing, summaries,
    and aggregated performance metrics.
    """
    queryset = Experiment.objects.all().order_by('-created_at')
    serializer_class = ExperimentSerializer

    def get_queryset(self):
        qs = super().get_queryset()
        model_id = self.request.query_params.get('model_id')
        exp_type = self.request.query_params.get('type')
        version = self.request.query_params.get('version')
        if model_id:
            qs = qs.filter(model_id=model_id)
        if exp_type:
            qs = qs.filter(type=exp_type)
        if version:
            qs = qs.filter(version=version)
        return qs

    # GET /experiments/{id}/runs/
    @action(detail=True, methods=['get'])
    def runs(self, request, pk=None):
        experiment = self.get_object()
        status_filter = request.query_params.get('status')
        runs = Run.objects.filter(experiment=experiment)
        if status_filter:
            runs = runs.filter(status=status_filter)
        runs = runs.order_by('-created_at')
        serializer = RunSerializer(runs, many=True)
        return Response(serializer.data)

    # GET /experiments/{id}/summary/
    @action(detail=True, methods=['get'])
    def summary(self, request, pk=None):
        experiment = self.get_object()
        runs = Run.objects.filter(experiment=experiment)
        metrics = RunMetric.objects.filter(run__in=runs)
        metric_agg = metrics.values('metric_name').annotate(
            avg=Avg('metric_value'),
            min=Min('metric_value'),
            max=Max('metric_value'),
        )
        return Response({
            'experiment': ExperimentSerializer(experiment).data,
            'total_runs': runs.count(),
            'success_rate': _run_success_rate(runs),
            'metric_aggregates': list(metric_agg),
        })

    # GET /experiments/{id}/materials/
    @action(detail=True, methods=['get'])
    def materials(self, request, pk=None):
        experiment = self.get_object()
        links = ExperimentMaterial.objects.filter(experiment=experiment).select_related('material')
        data = []
        for link in links:
            entry = MaterialSerializer(link.material).data
            entry['role'] = link.role
            entry['notes'] = link.notes
            data.append(entry)
        return Response(data)


# -----------------------------------------------------------------------------
# RUN VIEWSET
# -----------------------------------------------------------------------------

class RunViewSet(viewsets.ModelViewSet):
    """
    Full CRUD for runs plus logs, metrics, outputs, timeline,
    and aggregated summaries.
    """
    queryset = Run.objects.all().order_by('-created_at')
    serializer_class = RunSerializer

    def get_queryset(self):
        qs = super().get_queryset()
        experiment_id = self.request.query_params.get('experiment_id')
        setup_id = self.request.query_params.get('setup_id')
        run_status = self.request.query_params.get('status')
        if experiment_id:
            qs = qs.filter(experiment_id=experiment_id)
        if setup_id:
            qs = qs.filter(setup_id=setup_id)
        if run_status:
            qs = qs.filter(status=run_status)
        return qs

    # GET /runs/{id}/logs/
    @action(detail=True, methods=['get'])
    def logs(self, request, pk=None):
        run = self.get_object()
        level = request.query_params.get('level')
        since = request.query_params.get('since')
        until = request.query_params.get('until')
        qs = RunLog.objects.filter(run=run)
        if level:
            qs = qs.filter(level=level)
        if since:
            qs = qs.filter(logged_at__gte=since)
        if until:
            qs = qs.filter(logged_at__lte=until)
        qs = qs.order_by('logged_at')
        serializer = RunLogSerializer(qs, many=True)
        return Response(serializer.data)

    # GET /runs/{id}/metrics/
    @action(detail=True, methods=['get'])
    def metrics(self, request, pk=None):
        run = self.get_object()
        metrics = RunMetric.objects.filter(run=run)
        serializer = RunMetricSerializer(metrics, many=True)
        return Response(serializer.data)

    # GET /runs/{id}/outputs/
    @action(detail=True, methods=['get'])
    def outputs(self, request, pk=None):
        run = self.get_object()
        output_type = request.query_params.get('type')
        qs = RunOutput.objects.filter(run=run)
        if output_type:
            qs = qs.filter(type=output_type)
        serializer = RunOutputSerializer(qs, many=True)
        return Response(serializer.data)

    # GET /runs/{id}/timeline/
    @action(detail=True, methods=['get'])
    def timeline(self, request, pk=None):
        run = self.get_object()
        logs = RunLog.objects.filter(run=run).order_by('logged_at')
        outputs = RunOutput.objects.filter(run=run).order_by('created_at')
        events = []
        for log in logs:
            events.append({
                'type': 'log',
                'level': log.level,
                'message': log.message,
                'timestamp': log.logged_at,
            })
        for output in outputs:
            events.append({
                'type': 'output',
                'output_type': output.type,
                'name': output.name,
                'timestamp': output.created_at,
            })
        events.sort(key=lambda e: e['timestamp'])
        return Response({
            'run_id': run.id,
            'started_at': run.started_at,
            'finished_at': run.finished_at,
            'status': run.status,
            'events': events,
        })

    # GET /runs/{id}/summary/
    @action(detail=True, methods=['get'])
    def summary(self, request, pk=None):
        run = self.get_object()
        metrics = RunMetric.objects.filter(run=run)
        logs = RunLog.objects.filter(run=run)
        outputs = RunOutput.objects.filter(run=run)
        duration = None
        if run.started_at and run.finished_at:
            duration = (run.finished_at - run.started_at).total_seconds()
        return Response({
            'run': RunSerializer(run).data,
            'duration_seconds': duration,
            'metrics': RunMetricSerializer(metrics, many=True).data,
            'log_counts': {
                level: logs.filter(level=level).count()
                for level in ['info', 'warning', 'error']
            },
            'output_count': outputs.count(),
        })

    # POST /runs/compare_metrics/   body: {"run_ids": [1,2,3]}
    @action(detail=False, methods=['post'])
    def compare_metrics(self, request):
        run_ids = request.data.get('run_ids', [])
        if not run_ids:
            return Response({'error': 'run_ids is required'}, status=status.HTTP_400_BAD_REQUEST)
        runs = Run.objects.filter(id__in=run_ids)
        result = {}
        for run in runs:
            metrics = RunMetric.objects.filter(run=run)
            result[run.id] = {
                m.metric_name: m.metric_value for m in metrics
            }
        return Response(result)


# -----------------------------------------------------------------------------
# SETUP VIEWSET
# -----------------------------------------------------------------------------

class SetupViewSet(viewsets.ModelViewSet):
    """
    Full CRUD for setups plus platform linkage, run listing,
    and merged configuration.
    """
    queryset = Setup.objects.all().order_by('-created_at')
    serializer_class = SetupSerializer

    # GET /setups/{id}/platforms/
    @action(detail=True, methods=['get'])
    def platforms(self, request, pk=None):
        setup = self.get_object()
        links = SetupPlatform.objects.filter(setup=setup).select_related('platform')
        data = []
        for link in links:
            entry = PlatformSerializer(link.platform).data
            entry['role'] = link.role
            entry['config'] = link.config
            data.append(entry)
        return Response(data)

    # GET /setups/{id}/runs/
    @action(detail=True, methods=['get'])
    def runs(self, request, pk=None):
        setup = self.get_object()
        runs = Run.objects.filter(setup=setup).order_by('-created_at')
        serializer = RunSerializer(runs, many=True)
        return Response(serializer.data)

    # GET /setups/{id}/config/
    @action(detail=True, methods=['get'])
    def config(self, request, pk=None):
        setup = self.get_object()
        merged = {}
        for sp in SetupPlatform.objects.filter(setup=setup):
            if sp.config:
                merged[sp.platform.name] = sp.config
        return Response({
            'setup_id': setup.id,
            'setup_name': setup.name,
            'platform_configs': merged,
        })


# -----------------------------------------------------------------------------
# PLATFORM VIEWSET
# -----------------------------------------------------------------------------

class PlatformViewSet(viewsets.ModelViewSet):
    """
    Full CRUD for platforms plus setup linkage and run usage tracking.
    """
    queryset = Platform.objects.all().order_by('-created_at')
    serializer_class = PlatformSerializer

    # GET /platforms/{id}/setups/
    @action(detail=True, methods=['get'])
    def setups(self, request, pk=None):
        platform = self.get_object()
        links = SetupPlatform.objects.filter(platform=platform).select_related('setup')
        data = []
        for link in links:
            entry = SetupSerializer(link.setup).data
            entry['role'] = link.role
            entry['config'] = link.config
            data.append(entry)
        return Response(data)

    # GET /platforms/{id}/runs/
    @action(detail=True, methods=['get'])
    def runs(self, request, pk=None):
        platform = self.get_object()
        setup_ids = SetupPlatform.objects.filter(platform=platform).values_list('setup_id', flat=True)
        runs = Run.objects.filter(setup_id__in=setup_ids).order_by('-created_at')
        serializer = RunSerializer(runs, many=True)
        return Response(serializer.data)


# -----------------------------------------------------------------------------
# MATERIAL VIEWSET
# -----------------------------------------------------------------------------

class MaterialViewSet(viewsets.ModelViewSet):
    """
    Full CRUD for materials plus linkage to models/experiments,
    usage tracking, and dependency exploration.
    """
    queryset = Material.objects.all().order_by('-created_at')
    serializer_class = MaterialSerializer

    def get_queryset(self):
        qs = super().get_queryset()
        material_type_id = self.request.query_params.get('material_type_id')
        version = self.request.query_params.get('version')
        name = self.request.query_params.get('name')
        if material_type_id:
            qs = qs.filter(material_type_id=material_type_id)
        if version:
            qs = qs.filter(version=version)
        if name:
            qs = qs.filter(name__icontains=name)
        return qs

    # GET /materials/{id}/models/
    @action(detail=True, methods=['get'])
    def models(self, request, pk=None):
        material = self.get_object()
        links = ModelMaterial.objects.filter(material=material).select_related('model')
        data = []
        for link in links:
            entry = ModelSerializer(link.model).data
            entry['relation_type'] = link.relation_type
            data.append(entry)
        return Response(data)

    # GET /materials/{id}/experiments/
    @action(detail=True, methods=['get'])
    def experiments(self, request, pk=None):
        material = self.get_object()
        links = ExperimentMaterial.objects.filter(material=material).select_related('experiment')
        data = []
        for link in links:
            entry = ExperimentSerializer(link.experiment).data
            entry['role'] = link.role
            entry['notes'] = link.notes
            data.append(entry)
        return Response(data)

    # GET /materials/{id}/usage/
    @action(detail=True, methods=['get'])
    def usage(self, request, pk=None):
        material = self.get_object()
        model_count = ModelMaterial.objects.filter(material=material).count()
        experiment_count = ExperimentMaterial.objects.filter(material=material).count()
        return Response({
            'material_id': material.id,
            'used_in_models': model_count,
            'used_in_experiments': experiment_count,
        })


# -----------------------------------------------------------------------------
# MATERIAL TYPE VIEWSET
# -----------------------------------------------------------------------------

class MaterialTypeViewSet(viewsets.ModelViewSet):
    """
    Full CRUD for material types plus listing of materials under each type.
    """
    queryset = MaterialType.objects.all()
    serializer_class = MaterialTypeSerializer

    # GET /material-types/{id}/materials/
    @action(detail=True, methods=['get'])
    def materials(self, request, pk=None):
        material_type = self.get_object()
        materials = Material.objects.filter(material_type=material_type).order_by('-created_at')
        serializer = MaterialSerializer(materials, many=True)
        return Response(serializer.data)


# =============================================================================
# RELATIONSHIP LAYER VIEWSETS
# =============================================================================

class SetupPlatformViewSet(viewsets.ModelViewSet):
    queryset = SetupPlatform.objects.all()
    serializer_class = SetupPlatformSerializer

    def get_queryset(self):
        qs = super().get_queryset()
        setup_id = self.request.query_params.get('setup_id')
        platform_id = self.request.query_params.get('platform_id')
        if setup_id:
            qs = qs.filter(setup_id=setup_id)
        if platform_id:
            qs = qs.filter(platform_id=platform_id)
        return qs


class ExperimentMaterialViewSet(viewsets.ModelViewSet):
    queryset = ExperimentMaterial.objects.all()
    serializer_class = ExperimentMaterialSerializer

    def get_queryset(self):
        qs = super().get_queryset()
        experiment_id = self.request.query_params.get('experiment_id')
        material_id = self.request.query_params.get('material_id')
        if experiment_id:
            qs = qs.filter(experiment_id=experiment_id)
        if material_id:
            qs = qs.filter(material_id=material_id)
        return qs


class ModelMaterialViewSet(viewsets.ModelViewSet):
    queryset = ModelMaterial.objects.all()
    serializer_class = ModelMaterialSerializer

    def get_queryset(self):
        qs = super().get_queryset()
        model_id = self.request.query_params.get('model_id')
        material_id = self.request.query_params.get('material_id')
        if model_id:
            qs = qs.filter(model_id=model_id)
        if material_id:
            qs = qs.filter(material_id=material_id)
        return qs


# =============================================================================
# OBSERVABILITY LAYER VIEWSETS
# =============================================================================

class RunLogViewSet(viewsets.ModelViewSet):
    """
    Retrieve, filter, and create run logs.
    Supports filtering by level and time range.
    """
    queryset = RunLog.objects.all().order_by('logged_at')
    serializer_class = RunLogSerializer

    def get_queryset(self):
        qs = super().get_queryset()
        run_id = self.request.query_params.get('run_id')
        level = self.request.query_params.get('level')
        since = self.request.query_params.get('since')
        until = self.request.query_params.get('until')
        if run_id:
            qs = qs.filter(run_id=run_id)
        if level:
            qs = qs.filter(level=level)
        if since:
            qs = qs.filter(logged_at__gte=since)
        if until:
            qs = qs.filter(logged_at__lte=until)
        return qs


class RunMetricViewSet(viewsets.ModelViewSet):
    """
    Retrieve and manage run metrics.
    Supports aggregation across experiments.
    """
    queryset = RunMetric.objects.all()
    serializer_class = RunMetricSerializer

    def get_queryset(self):
        qs = super().get_queryset()
        run_id = self.request.query_params.get('run_id')
        metric_name = self.request.query_params.get('metric_name')
        if run_id:
            qs = qs.filter(run_id=run_id)
        if metric_name:
            qs = qs.filter(metric_name=metric_name)
        return qs

    # GET /run-metrics/aggregate/?experiment_id=X&metric_name=Y
    @action(detail=False, methods=['get'])
    def aggregate(self, request):
        experiment_id = request.query_params.get('experiment_id')
        metric_name = request.query_params.get('metric_name')
        if not experiment_id or not metric_name:
            return Response(
                {'error': 'experiment_id and metric_name are required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        runs = Run.objects.filter(experiment_id=experiment_id)
        agg = RunMetric.objects.filter(
            run__in=runs, metric_name=metric_name
        ).aggregate(avg=Avg('metric_value'), min=Min('metric_value'), max=Max('metric_value'))
        return Response({
            'experiment_id': experiment_id,
            'metric_name': metric_name,
            **agg,
        })


class RunOutputViewSet(viewsets.ModelViewSet):
    """
    List, create, and download run outputs (files, artifacts, results).
    """
    queryset = RunOutput.objects.all().order_by('-created_at')
    serializer_class = RunOutputSerializer

    def get_queryset(self):
        qs = super().get_queryset()
        run_id = self.request.query_params.get('run_id')
        output_type = self.request.query_params.get('type')
        if run_id:
            qs = qs.filter(run_id=run_id)
        if output_type:
            qs = qs.filter(type=output_type)
        return qs


# =============================================================================
# PARAMETER SYSTEM
# =============================================================================

class ParameterViewSet(viewsets.ModelViewSet):
    """
    Polymorphic key-value metadata across all entity types.
    Supports listing, bulk update, and search.
    """
    queryset = Parameter.objects.all().order_by('-created_at')
    serializer_class = ParameterSerializer

    def get_queryset(self):
        qs = super().get_queryset()
        entity_type = self.request.query_params.get('entity_type')
        entity_id = self.request.query_params.get('entity_id')
        key = self.request.query_params.get('key')
        if entity_type:
            qs = qs.filter(entity_type=entity_type)
        if entity_id:
            qs = qs.filter(entity_id=entity_id)
        if key:
            qs = qs.filter(key__icontains=key)
        return qs

    # POST /parameters/bulk_update/
    # body: [{"entity_type": "run", "entity_id": 1, "key": "lr", "value": "0.01", "value_type": "float"}, ...]
    @action(detail=False, methods=['post'])
    def bulk_update(self, request):
        items = request.data
        if not isinstance(items, list):
            return Response({'error': 'Expected a list of parameter objects'}, status=status.HTTP_400_BAD_REQUEST)
        created = []
        for item in items:
            param, _ = Parameter.objects.update_or_create(
                entity_type=item.get('entity_type'),
                entity_id=item.get('entity_id'),
                key=item.get('key'),
                defaults={
                    'value': item.get('value'),
                    'value_type': item.get('value_type'),
                }
            )
            created.append(ParameterSerializer(param).data)
        return Response(created, status=status.HTTP_200_OK)

    # GET /parameters/search/?q=learning_rate
    @action(detail=False, methods=['get'])
    def search(self, request):
        q = request.query_params.get('q', '')
        qs = Parameter.objects.filter(
            Q(key__icontains=q) | Q(value__icontains=q)
        )
        serializer = ParameterSerializer(qs, many=True)
        return Response(serializer.data)


# =============================================================================
# TAGGING SYSTEM
# =============================================================================

class TagViewSet(viewsets.ModelViewSet):
    """
    CRUD for tags plus assigning/removing tags from entities
    and querying entities by tag.
    """
    queryset = Tag.objects.all().order_by('name')
    serializer_class = TagSerializer

    # POST /tags/{id}/assign/
    # body: {"entity_type": "run", "entity_id": 5}
    @action(detail=True, methods=['post'])
    def assign(self, request, pk=None):
        tag = self.get_object()
        entity_type = request.data.get('entity_type')
        entity_id = request.data.get('entity_id')
        if not entity_type or not entity_id:
            return Response({'error': 'entity_type and entity_id are required'}, status=status.HTTP_400_BAD_REQUEST)
        et, created = EntityTag.objects.get_or_create(tag=tag, entity_type=entity_type, entity_id=entity_id)
        return Response(EntityTagSerializer(et).data, status=status.HTTP_201_CREATED if created else status.HTTP_200_OK)

    # POST /tags/{id}/remove/
    # body: {"entity_type": "run", "entity_id": 5}
    @action(detail=True, methods=['post'])
    def remove(self, request, pk=None):
        tag = self.get_object()
        entity_type = request.data.get('entity_type')
        entity_id = request.data.get('entity_id')
        deleted, _ = EntityTag.objects.filter(tag=tag, entity_type=entity_type, entity_id=entity_id).delete()
        if deleted:
            return Response({'status': 'removed'})
        return Response({'status': 'not found'}, status=status.HTTP_404_NOT_FOUND)

    # GET /tags/{id}/entities/
    @action(detail=True, methods=['get'])
    def entities(self, request, pk=None):
        tag = self.get_object()
        entity_tags = EntityTag.objects.filter(tag=tag)
        serializer = EntityTagSerializer(entity_tags, many=True)
        return Response(serializer.data)


class EntityTagViewSet(viewsets.ModelViewSet):
    """
    Direct access to entity-tag relationships with filtering by entity.
    """
    queryset = EntityTag.objects.all()
    serializer_class = EntityTagSerializer

    def get_queryset(self):
        qs = super().get_queryset()
        entity_type = self.request.query_params.get('entity_type')
        entity_id = self.request.query_params.get('entity_id')
        tag_id = self.request.query_params.get('tag_id')
        if entity_type:
            qs = qs.filter(entity_type=entity_type)
        if entity_id:
            qs = qs.filter(entity_id=entity_id)
        if tag_id:
            qs = qs.filter(tag_id=tag_id)
        return qs


# =============================================================================
# SEARCH VIEW
# =============================================================================

class SearchView(APIView):
    """
    Cross-entity search across models, experiments, runs, materials, and tags.
    GET /search/?q=<query>[&entity=<type>][&status=<status>][&version=<version>]
    """

    def get(self, request):
        q = request.query_params.get('q', '').strip()
        entity = request.query_params.get('entity')  # optional filter to single entity type
        filter_status = request.query_params.get('status')
        filter_version = request.query_params.get('version')

        results = {}

        if not entity or entity == 'models':
            qs = Model.objects.filter(Q(name__icontains=q) | Q(description__icontains=q))
            if filter_version:
                qs = qs.filter(version=filter_version)
            results['models'] = ModelSerializer(qs, many=True).data

        if not entity or entity == 'experiments':
            qs = Experiment.objects.filter(Q(name__icontains=q) | Q(description__icontains=q))
            if filter_version:
                qs = qs.filter(version=filter_version)
            results['experiments'] = ExperimentSerializer(qs, many=True).data

        if not entity or entity == 'runs':
            qs = Run.objects.filter(Q(name__icontains=q) | Q(notes__icontains=q))
            if filter_status:
                qs = qs.filter(status=filter_status)
            results['runs'] = RunSerializer(qs, many=True).data

        if not entity or entity == 'materials':
            qs = Material.objects.filter(Q(name__icontains=q) | Q(description__icontains=q))
            if filter_version:
                qs = qs.filter(version=filter_version)
            results['materials'] = MaterialSerializer(qs, many=True).data

        if not entity or entity == 'tags':
            qs = Tag.objects.filter(name__icontains=q)
            results['tags'] = TagSerializer(qs, many=True).data

        return Response(results)


# =============================================================================
# DASHBOARD / ANALYTICS
# =============================================================================

class DashboardViewSet(viewsets.ViewSet):
    """
    Analytics dashboards at system, model, experiment, and run levels.
    """

    # GET /dashboard/global/
    @action(detail=False, methods=['get'])
    def global_overview(self, request):
        runs = Run.objects.all()
        return Response({
            'total_models': Model.objects.count(),
            'total_experiments': Experiment.objects.count(),
            'total_runs': runs.count(),
            'success_rate': _run_success_rate(runs),
            'active_runs': runs.filter(status='running').count(),
            'failed_runs': runs.filter(status='failed').count(),
            'pending_runs': runs.filter(status='pending').count(),
        })

    # GET /dashboard/model/?model_id=X
    @action(detail=False, methods=['get'])
    def model(self, request):
        model_id = request.query_params.get('model_id')
        if not model_id:
            return Response({'error': 'model_id is required'}, status=status.HTTP_400_BAD_REQUEST)
        try:
            model = Model.objects.get(pk=model_id)
        except Model.DoesNotExist:
            return Response({'error': 'Model not found'}, status=status.HTTP_404_NOT_FOUND)
        experiments = Experiment.objects.filter(model=model)
        runs = Run.objects.filter(experiment__in=experiments)
        metrics = RunMetric.objects.filter(run__in=runs)
        metric_trends = metrics.values('metric_name').annotate(
            avg=Avg('metric_value'), min=Min('metric_value'), max=Max('metric_value')
        )
        return Response({
            'model': ModelSerializer(model).data,
            'experiment_count': experiments.count(),
            'total_runs': runs.count(),
            'success_rate': _run_success_rate(runs),
            'metric_trends': list(metric_trends),
        })

    # GET /dashboard/experiment/?experiment_id=X
    @action(detail=False, methods=['get'])
    def experiment(self, request):
        experiment_id = request.query_params.get('experiment_id')
        if not experiment_id:
            return Response({'error': 'experiment_id is required'}, status=status.HTTP_400_BAD_REQUEST)
        try:
            experiment = Experiment.objects.get(pk=experiment_id)
        except Experiment.DoesNotExist:
            return Response({'error': 'Experiment not found'}, status=status.HTTP_404_NOT_FOUND)
        runs = Run.objects.filter(experiment=experiment).order_by('created_at')
        metrics = RunMetric.objects.filter(run__in=runs)
        metric_evolution = metrics.values('metric_name').annotate(
            avg=Avg('metric_value'), min=Min('metric_value'), max=Max('metric_value')
        )
        best_run = runs.filter(status='successful').order_by('-started_at').first()
        worst_run = runs.filter(status='failed').order_by('-started_at').first()
        return Response({
            'experiment': ExperimentSerializer(experiment).data,
            'total_runs': runs.count(),
            'success_rate': _run_success_rate(runs),
            'best_run': RunSerializer(best_run).data if best_run else None,
            'worst_run': RunSerializer(worst_run).data if worst_run else None,
            'metric_evolution': list(metric_evolution),
        })

    # GET /dashboard/run/?run_id=X
    @action(detail=False, methods=['get'])
    def run(self, request):
        run_id = request.query_params.get('run_id')
        if not run_id:
            return Response({'error': 'run_id is required'}, status=status.HTTP_400_BAD_REQUEST)
        try:
            run = Run.objects.get(pk=run_id)
        except Run.DoesNotExist:
            return Response({'error': 'Run not found'}, status=status.HTTP_404_NOT_FOUND)
        logs = RunLog.objects.filter(run=run)
        metrics = RunMetric.objects.filter(run=run)
        outputs = RunOutput.objects.filter(run=run)
        duration = None
        if run.started_at and run.finished_at:
            duration = (run.finished_at - run.started_at).total_seconds()
        log_distribution = {
            level: logs.filter(level=level).count()
            for level in ['info', 'warning', 'error']
        }
        return Response({
            'run': RunSerializer(run).data,
            'duration_seconds': duration,
            'log_distribution': log_distribution,
            'metric_count': metrics.count(),
            'metrics': RunMetricSerializer(metrics, many=True).data,
            'output_count': outputs.count(),
        })


# =============================================================================
# GRAPH / RELATIONSHIP TRAVERSAL
# =============================================================================

class GraphViewSet(viewsets.ViewSet):
    """
    Graph traversal endpoints for visualizing entity relationships.
    """

    # GET /graph/model/?model_id=X
    @action(detail=False, methods=['get'])
    def model(self, request):
        model_id = request.query_params.get('model_id')
        if not model_id:
            return Response({'error': 'model_id is required'}, status=status.HTTP_400_BAD_REQUEST)
        try:
            model = Model.objects.get(pk=model_id)
        except Model.DoesNotExist:
            return Response({'error': 'Model not found'}, status=status.HTTP_404_NOT_FOUND)

        experiments = Experiment.objects.filter(model=model)
        materials = ModelMaterial.objects.filter(model=model).select_related('material')
        children = Model.objects.filter(parent_model=model)
        parent = model.parent_model

        return Response({
            'model': ModelSerializer(model).data,
            'parent': ModelSerializer(parent).data if parent else None,
            'children': ModelSerializer(children, many=True).data,
            'experiments': ExperimentSerializer(experiments, many=True).data,
            'materials': [
                {**MaterialSerializer(mm.material).data, 'relation_type': mm.relation_type}
                for mm in materials
            ],
        })

    # GET /graph/experiment/?experiment_id=X
    @action(detail=False, methods=['get'])
    def experiment(self, request):
        experiment_id = request.query_params.get('experiment_id')
        if not experiment_id:
            return Response({'error': 'experiment_id is required'}, status=status.HTTP_400_BAD_REQUEST)
        try:
            experiment = Experiment.objects.get(pk=experiment_id)
        except Experiment.DoesNotExist:
            return Response({'error': 'Experiment not found'}, status=status.HTTP_404_NOT_FOUND)

        runs = Run.objects.filter(experiment=experiment)
        setup_ids = runs.values_list('setup_id', flat=True).distinct()
        setups = Setup.objects.filter(id__in=setup_ids)
        platform_ids = SetupPlatform.objects.filter(setup__in=setups).values_list('platform_id', flat=True).distinct()
        platforms = Platform.objects.filter(id__in=platform_ids)
        platform_dist = {}
        for platform in platforms:
            setup_ids_for_platform = SetupPlatform.objects.filter(platform=platform).values_list('setup_id', flat=True)
            platform_dist[platform.name] = runs.filter(setup_id__in=setup_ids_for_platform).count()

        return Response({
            'experiment': ExperimentSerializer(experiment).data,
            'runs': RunSerializer(runs, many=True).data,
            'setups': SetupSerializer(setups, many=True).data,
            'platform_distribution': platform_dist,
        })


# =============================================================================
# ACTIVITY FEED
# =============================================================================

class ActivityView(APIView):
    """
    System-wide activity feed showing recent models, experiments, and run failures.
    GET /activity/?limit=20
    """

    def get(self, request):
        limit = int(request.query_params.get('limit', 20))
        recent_models = Model.objects.order_by('-created_at')[:limit]
        recent_experiments = Experiment.objects.order_by('-created_at')[:limit]
        recent_failures = Run.objects.filter(status='failed').order_by('-finished_at')[:limit]
        active_runs = Run.objects.filter(status='running').order_by('-started_at')[:limit]
        return Response({
            'recent_models': ModelSerializer(recent_models, many=True).data,
            'recent_experiments': ExperimentSerializer(recent_experiments, many=True).data,
            'recent_failures': RunSerializer(recent_failures, many=True).data,
            'active_runs': RunSerializer(active_runs, many=True).data,
        })


# =============================================================================
# MODEL COMPARISON
# =============================================================================

class ModelComparisonView(APIView):
    """
    Compare multiple models across experiment performance, run metrics,
    and material usage.
    POST /compare/models/   body: {"model_ids": [1, 2, 3]}
    """

    def post(self, request):
        model_ids = request.data.get('model_ids', [])
        if len(model_ids) < 2:
            return Response({'error': 'Provide at least two model_ids'}, status=status.HTTP_400_BAD_REQUEST)

        result = []
        for model_id in model_ids:
            try:
                model = Model.objects.get(pk=model_id)
            except Model.DoesNotExist:
                continue
            experiments = Experiment.objects.filter(model=model)
            runs = Run.objects.filter(experiment__in=experiments)
            metrics = RunMetric.objects.filter(run__in=runs)
            metric_agg = metrics.values('metric_name').annotate(
                avg=Avg('metric_value'), min=Min('metric_value'), max=Max('metric_value')
            )
            material_count = ModelMaterial.objects.filter(model=model).count()
            result.append({
                'model': ModelSerializer(model).data,
                'experiment_count': experiments.count(),
                'total_runs': runs.count(),
                'success_rate': _run_success_rate(runs),
                'metric_aggregates': list(metric_agg),
                'material_count': material_count,
            })
        return Response(result)


# =============================================================================
# VERSION TRACKING
# =============================================================================

class VersionTrackingView(APIView):
    """
    Retrieve the version history for a model or material.
    GET /versions/?entity=model&name=MyModel
    GET /versions/?entity=material&name=MyDataset
    """

    def get(self, request):
        entity = request.query_params.get('entity')
        name = request.query_params.get('name')
        if not entity or not name:
            return Response({'error': 'entity and name are required'}, status=status.HTTP_400_BAD_REQUEST)

        if entity == 'model':
            qs = Model.objects.filter(name=name).order_by('created_at')
            return Response(ModelSerializer(qs, many=True).data)
        elif entity == 'material':
            qs = Material.objects.filter(name=name).order_by('created_at')
            return Response(MaterialSerializer(qs, many=True).data)
        else:
            return Response({'error': 'entity must be "model" or "material"'}, status=status.HTTP_400_BAD_REQUEST)