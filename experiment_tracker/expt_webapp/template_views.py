from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.db.models import Count, Avg, Q, Max, Min
from django.utils import timezone

from .models import (
    Model, Experiment, Run, Setup, Platform,
    SetupPlatform, ExperimentMaterial, ModelMaterial, ExperimentSetup,
    MaterialType, Material, Parameter, RunMetric,
    RunOutput, RunLog, Tag, EntityTag,
)


# =============================================================================
# HELPERS
# =============================================================================

def _run_success_rate(runs_qs):
    total = runs_qs.count()
    if total == 0:
        return None
    return round(runs_qs.filter(status='successful').count() / total * 100, 1)


def _run_duration(run):
    if run.started_at and run.finished_at:
        delta = run.finished_at - run.started_at
        total = int(delta.total_seconds())
        h, rem = divmod(total, 3600)
        m, s = divmod(rem, 60)
        if h:
            return f"{h}h {m}m {s}s"
        elif m:
            return f"{m}m {s}s"
        return f"{s}s"
    return None


RUN_STATUSES = ['pending', 'running', 'successful', 'failed', 'cancelled']


# =============================================================================
# DASHBOARD
# =============================================================================

def dashboard(request):
    runs = Run.objects.all()
    ctx = {
        'stats': {
            'total_models':      Model.objects.count(),
            'total_experiments': Experiment.objects.count(),
            'total_runs':        runs.count(),
            'active_runs':       runs.filter(status='running').count(),
            'failed_runs':       runs.filter(status='failed').count(),
            'success_rate':      _run_success_rate(runs),
        },
        'recent_models':      Model.objects.order_by('-created_at')[:8],
        'recent_experiments': Experiment.objects.select_related('model').order_by('-created_at')[:8],
        'active_runs':        Run.objects.select_related('experiment').filter(status='running').order_by('-started_at')[:8],
        'recent_failures':    Run.objects.select_related('experiment').filter(status='failed').order_by('-finished_at')[:8],
    }
    return render(request, 'expt_webapp/dashboard.html', ctx)


# =============================================================================
# MODELS
# =============================================================================

def model_list(request):
    qs = Model.objects.all().order_by('-created_at')
    if request.GET.get('name'):
        qs = qs.filter(name__icontains=request.GET['name'])
    if request.GET.get('version'):
        qs = qs.filter(version=request.GET['version'])
    return render(request, 'expt_webapp/models/list.html', {'models': qs})


def model_detail(request, pk):
    model = get_object_or_404(Model, pk=pk)

    if request.method == 'POST':
        action = request.POST.get('action')
        if action == 'add_material':
            material_id   = request.POST.get('material_id')
            relation_type = request.POST.get('relation_type') or None
            if material_id:
                ModelMaterial.objects.get_or_create(
                    model=model, material_id=material_id,
                    defaults={'relation_type': relation_type},
                )
                messages.success(request, 'Material linked.')
        elif action == 'remove_material':
            ModelMaterial.objects.filter(model=model, material_id=request.POST.get('material_id')).delete()
            messages.success(request, 'Material unlinked.')
        return redirect('model-detail', pk=pk)

    experiments = Experiment.objects.filter(model=model).annotate(
        run_count=Count('run')
    ).order_by('-created_at')
    runs = Run.objects.filter(experiment__model=model)
    children = Model.objects.filter(parent_model=model)
    model_materials = ModelMaterial.objects.filter(model=model).select_related('material__material_type')
    linked_ids = model_materials.values_list('material_id', flat=True)
    available_materials = Material.objects.exclude(id__in=linked_ids).select_related('material_type').order_by('name')
    tags = EntityTag.objects.filter(entity_type='model', entity_id=pk).select_related('tag')
    ctx = {
        'model': model,
        'experiments': experiments,
        'children': children,
        'model_materials': model_materials,
        'available_materials': available_materials,
        'tags': tags,
        'stats': {
            'total_experiments': experiments.count(),
            'total_runs':        runs.count(),
            'active_runs':       runs.filter(status='running').count(),
            'failed_runs':       runs.filter(status='failed').count(),
            'success_rate':      _run_success_rate(runs),
        },
    }
    return render(request, 'expt_webapp/models/detail.html', ctx)


def model_create(request):
    if request.method == 'POST':
        parent_id = request.POST.get('parent_model') or None
        model = Model.objects.create(
            name=request.POST['name'],
            version=request.POST['version'],
            description=request.POST.get('description') or None,
            parent_model_id=parent_id,
        )
        messages.success(request, f'Model "{model.name}" created.')
        return redirect('model-detail', pk=model.pk)
    return render(request, 'expt_webapp/models/form.html', {
        'all_models': Model.objects.all().order_by('name'),
    })


def model_edit(request, pk):
    model = get_object_or_404(Model, pk=pk)
    if request.method == 'POST':
        model.name = request.POST['name']
        model.version = request.POST['version']
        model.description = request.POST.get('description') or None
        model.parent_model_id = request.POST.get('parent_model') or None
        model.save()
        messages.success(request, 'Model updated.')
        return redirect('model-detail', pk=model.pk)
    return render(request, 'expt_webapp/models/form.html', {
        'model': model,
        'all_models': Model.objects.all().order_by('name'),
    })


# =============================================================================
# EXPERIMENTS
# =============================================================================

def experiment_list(request):
    qs = Experiment.objects.select_related('model').annotate(
        run_count=Count('run')
    ).order_by('-created_at')
    if request.GET.get('name'):
        qs = qs.filter(name__icontains=request.GET['name'])
    if request.GET.get('model_id'):
        qs = qs.filter(model_id=request.GET['model_id'])
    if request.GET.get('type'):
        qs = qs.filter(type__icontains=request.GET['type'])
    return render(request, 'expt_webapp/experiments/list.html', {
        'experiments': qs,
        'all_models':  Model.objects.all().order_by('name'),
    })


def experiment_detail(request, pk):
    experiment = get_object_or_404(Experiment.objects.select_related('model'), pk=pk)

    # Handle material link/unlink actions
    if request.method == 'POST':
        action = request.POST.get('action')
        if action == 'add_material':
            material_id = request.POST.get('material_id')
            role = request.POST.get('role') or None
            notes = request.POST.get('notes') or None
            if material_id:
                ExperimentMaterial.objects.get_or_create(
                    experiment=experiment,
                    material_id=material_id,
                    defaults={'role': role, 'notes': notes},
                )
                messages.success(request, 'Material linked.')
        elif action == 'remove_material':
            material_id = request.POST.get('material_id')
            ExperimentMaterial.objects.filter(experiment=experiment, material_id=material_id).delete()
            messages.success(request, 'Material unlinked.')
        return redirect('experiment-detail', pk=pk)

    runs_qs = Run.objects.filter(experiment=experiment).select_related('setup')
    if request.GET.get('status'):
        runs_qs = runs_qs.filter(status=request.GET['status'])
    runs_qs = runs_qs.order_by('-created_at')

    # Annotate duration
    runs = list(runs_qs)
    for r in runs:
        r.duration = _run_duration(r)

    experiment_materials = ExperimentMaterial.objects.filter(
        experiment=experiment
    ).select_related('material__material_type')
    experiment_setups = ExperimentSetup.objects.filter(
        experiment=experiment
    ).select_related('setup')

    # Materials not yet linked to this experiment
    linked_ids = experiment_materials.values_list('material_id', flat=True)
    available_materials = Material.objects.exclude(id__in=linked_ids).select_related('material_type').order_by('name')

    metrics = RunMetric.objects.filter(run__experiment=experiment)
    metric_aggregates = metrics.values('metric_name').annotate(
        avg=Avg('metric_value'), min=Min('metric_value'), max=Max('metric_value')
    )

    all_runs = Run.objects.filter(experiment=experiment)
    ctx = {
        'experiment':           experiment,
        'runs':                 runs,
        'statuses':             RUN_STATUSES,
        'experiment_materials': experiment_materials,
        'experiment_setups':    experiment_setups,
        'available_materials':  available_materials,
        'metric_aggregates':    metric_aggregates,
        'stats': {
            'total_runs':   all_runs.count(),
            'active_runs':  all_runs.filter(status='running').count(),
            'failed_runs':  all_runs.filter(status='failed').count(),
            'success_rate': _run_success_rate(all_runs),
        },
    }
    return render(request, 'expt_webapp/experiments/detail.html', ctx)


def experiment_create(request):
    if request.method == 'POST':
        setup_ids = request.POST.getlist('setups')
        if not setup_ids:
            return render(request, 'expt_webapp/experiments/form.html', {
                'all_models': Model.objects.all().order_by('name'),
                'all_setups': Setup.objects.all().order_by('name'),
                'error': 'At least one setup is required.',
            })
        exp = Experiment.objects.create(
            model_id=request.POST['model'],
            name=request.POST['name'],
            version=request.POST['version'],
            type=request.POST.get('type') or None,
            description=request.POST.get('description') or None,
        )
        for sid in setup_ids:
            ExperimentSetup.objects.create(experiment=exp, setup_id=sid)
        messages.success(request, f'Experiment "{exp.name}" created.')
        return redirect('experiment-detail', pk=exp.pk)
    return render(request, 'expt_webapp/experiments/form.html', {
        'all_models': Model.objects.all().order_by('name'),
        'all_setups': Setup.objects.all().order_by('name'),
    })


def experiment_edit(request, pk):
    experiment = get_object_or_404(Experiment, pk=pk)
    if request.method == 'POST':
        setup_ids = request.POST.getlist('setups')
        if not setup_ids:
            current_setup_ids = list(ExperimentSetup.objects.filter(experiment=experiment).values_list('setup_id', flat=True))
            return render(request, 'expt_webapp/experiments/form.html', {
                'experiment': experiment,
                'all_models': Model.objects.all().order_by('name'),
                'all_setups': Setup.objects.all().order_by('name'),
                'selected_setup_ids': current_setup_ids,
                'error': 'At least one setup is required.',
            })
        experiment.model_id = request.POST['model']
        experiment.name = request.POST['name']
        experiment.version = request.POST['version']
        experiment.type = request.POST.get('type') or None
        experiment.description = request.POST.get('description') or None
        experiment.save()
        # Update setups
        ExperimentSetup.objects.filter(experiment=experiment).delete()
        for sid in setup_ids:
            ExperimentSetup.objects.create(experiment=experiment, setup_id=sid)
        messages.success(request, 'Experiment updated.')
        return redirect('experiment-detail', pk=experiment.pk)
    current_setup_ids = list(ExperimentSetup.objects.filter(experiment=experiment).values_list('setup_id', flat=True))
    return render(request, 'expt_webapp/experiments/form.html', {
        'experiment': experiment,
        'all_models': Model.objects.all().order_by('name'),
        'all_setups': Setup.objects.all().order_by('name'),
        'selected_setup_ids': current_setup_ids,
    })


# =============================================================================
# RUNS
# =============================================================================

def run_list(request):
    qs = Run.objects.select_related('experiment__model', 'setup').order_by('-created_at')
    if request.GET.get('status'):
        qs = qs.filter(status=request.GET['status'])
    if request.GET.get('experiment_id'):
        qs = qs.filter(experiment_id=request.GET['experiment_id'])

    runs = list(qs)
    for r in runs:
        r.duration = _run_duration(r)

    return render(request, 'expt_webapp/runs/list.html', {
        'runs':            runs,
        'statuses':        RUN_STATUSES,
        'all_experiments': Experiment.objects.select_related('model').order_by('name'),
    })


def run_detail(request, pk):
    run = get_object_or_404(Run.objects.select_related('experiment__model', 'setup'), pk=pk)

    if request.method == 'POST':
        action = request.POST.get('action')

        if action == 'add_metric':
            metric_name  = request.POST.get('metric_name', '').strip()
            metric_value = request.POST.get('metric_value', '').strip()
            if metric_name and metric_value:
                RunMetric.objects.update_or_create(
                    run=run, metric_name=metric_name,
                    defaults={'metric_value': float(metric_value)},
                )
                messages.success(request, f'Metric "{metric_name}" saved.')

        elif action == 'delete_metric':
            RunMetric.objects.filter(run=run, metric_name=request.POST.get('metric_name')).delete()
            messages.success(request, 'Metric deleted.')

        elif action == 'add_log':
            level   = request.POST.get('level', 'info')
            message = request.POST.get('message', '').strip()
            if message:
                RunLog.objects.create(run=run, level=level, message=message)
                messages.success(request, 'Log entry added.')

        elif action == 'bulk_logs':
            import re as _re
            raw = request.POST.get('raw_logs', '').strip()
            # Parse common log formats:
            # [LEVEL] message
            # LEVEL: message
            # timestamp - LEVEL - message
            # INFO/WARNING/ERROR keywords anywhere at start of line
            pattern = _re.compile(
                r'^(?:[\d\-T:.Z\s]+[-\s]+)?'
                r'(INFO|WARNING|WARN|ERROR|DEBUG|CRITICAL)'
                r'[\s:\-]+(.+)$',
                _re.IGNORECASE
            )
            level_map = {'warn': 'warning', 'debug': 'info', 'critical': 'error'}
            created = 0
            for line in raw.splitlines():
                line = line.strip()
                if not line:
                    continue
                m = pattern.match(line)
                if m:
                    raw_level = m.group(1).lower()
                    lvl = level_map.get(raw_level, raw_level)
                    if lvl not in ('info', 'warning', 'error'):
                        lvl = 'info'
                    RunLog.objects.create(run=run, level=lvl, message=m.group(2).strip())
                else:
                    # Store unmatched lines as info
                    RunLog.objects.create(run=run, level='info', message=line)
                created += 1
            messages.success(request, f'{created} log entries imported.')

        elif action == 'delete_log':
            RunLog.objects.filter(run=run, id=request.POST.get('log_id')).delete()
            messages.success(request, 'Log deleted.')

        elif action == 'add_output':
            out_type = request.POST.get('out_type', 'result')
            name     = request.POST.get('name', '').strip() or None
            value    = request.POST.get('value', '').strip() or None
            RunOutput.objects.create(run=run, type=out_type, name=name, value=value)
            messages.success(request, 'Output added.')

        elif action == 'delete_output':
            RunOutput.objects.filter(run=run, id=request.POST.get('output_id')).delete()
            messages.success(request, 'Output deleted.')

        elif action == 'add_material':
            material_id = request.POST.get('material_id')
            role  = request.POST.get('role')  or None
            notes = request.POST.get('notes') or None
            if material_id:
                ExperimentMaterial.objects.get_or_create(
                    experiment=run.experiment, material_id=material_id,
                    defaults={'role': role, 'notes': notes},
                )
                messages.success(request, 'Material linked to experiment.')

        return redirect('run-detail', pk=pk)

    # Logs — optionally filtered by level
    logs_qs = RunLog.objects.filter(run=run).order_by('logged_at')
    if request.GET.get('log_level'):
        logs_qs = logs_qs.filter(level=request.GET['log_level'])

    metrics  = RunMetric.objects.filter(run=run)
    outputs  = RunOutput.objects.filter(run=run).order_by('created_at')
    all_logs = RunLog.objects.filter(run=run)

    # Build timeline from logs + outputs
    timeline = []
    for log in RunLog.objects.filter(run=run).order_by('logged_at'):
        timeline.append({
            'type':      'log',
            'level':     log.level,
            'message':   log.message,
            'timestamp': log.logged_at,
        })
    for out in RunOutput.objects.filter(run=run).order_by('created_at'):
        timeline.append({
            'type':        'output',
            'output_type': out.type,
            'name':        out.name,
            'timestamp':   out.created_at,
        })
    timeline.sort(key=lambda e: e['timestamp'])

    # Materials not yet linked to this run's experiment
    linked_ids = ExperimentMaterial.objects.filter(experiment=run.experiment).values_list('material_id', flat=True)
    available_materials = Material.objects.exclude(id__in=linked_ids).select_related('material_type').order_by('name')
    exp_materials = ExperimentMaterial.objects.filter(experiment=run.experiment).select_related('material__material_type')

    ctx = {
        'run':                 run,
        'metrics':             metrics,
        'logs':                logs_qs,
        'outputs':             outputs,
        'timeline':            timeline,
        'duration':            _run_duration(run),
        'available_materials': available_materials,
        'exp_materials':       exp_materials,
        'output_types':        RunOutput.OUTPUT_TYPES,
        'log_counts': {
            'info':    all_logs.filter(level='info').count(),
            'warning': all_logs.filter(level='warning').count(),
            'error':   all_logs.filter(level='error').count(),
        },
    }
    return render(request, 'expt_webapp/runs/detail.html', ctx)


def run_create(request):
    if request.method == 'POST':
        run = Run.objects.create(
            experiment_id=request.POST['experiment'],
            setup_id=request.POST['setup'],
            name=request.POST.get('name') or None,
            status=request.POST['status'],
            notes=request.POST.get('notes') or None,
            started_at=request.POST.get('started_at') or None,
            finished_at=request.POST.get('finished_at') or None,
        )
        messages.success(request, f'Run created.')
        return redirect('run-detail', pk=run.pk)
    return render(request, 'expt_webapp/runs/form.html', {
        'all_experiments': Experiment.objects.select_related('model').order_by('name'),
        'all_setups':      Setup.objects.all().order_by('name'),
        'statuses':        RUN_STATUSES,
    })


def run_edit(request, pk):
    run = get_object_or_404(Run, pk=pk)
    if request.method == 'POST':
        run.experiment_id = request.POST['experiment']
        run.setup_id      = request.POST['setup']
        run.name          = request.POST.get('name') or None
        run.status        = request.POST['status']
        run.notes         = request.POST.get('notes') or None
        run.started_at    = request.POST.get('started_at') or None
        run.finished_at   = request.POST.get('finished_at') or None
        run.save()
        messages.success(request, 'Run updated.')
        return redirect('run-detail', pk=run.pk)
    return render(request, 'expt_webapp/runs/form.html', {
        'run':             run,
        'all_experiments': Experiment.objects.select_related('model').order_by('name'),
        'all_setups':      Setup.objects.all().order_by('name'),
        'statuses':        RUN_STATUSES,
    })


# =============================================================================
# MATERIALS
# =============================================================================

def material_list(request):
    qs = Material.objects.select_related('material_type').order_by('-created_at')
    if request.GET.get('name'):
        qs = qs.filter(name__icontains=request.GET['name'])
    if request.GET.get('material_type_id'):
        qs = qs.filter(material_type_id=request.GET['material_type_id'])
    return render(request, 'expt_webapp/materials/list.html', {
        'materials':     qs,
        'material_types': MaterialType.objects.all().order_by('name'),
    })


def material_detail(request, pk):
    material = get_object_or_404(Material.objects.select_related('material_type'), pk=pk)
    model_links      = ModelMaterial.objects.filter(material=material).select_related('model')
    experiment_links = ExperimentMaterial.objects.filter(material=material).select_related('experiment')
    ctx = {
        'material':         material,
        'model_links':      model_links,
        'experiment_links': experiment_links,
        'usage': {
            'used_in_models':      model_links.count(),
            'used_in_experiments': experiment_links.count(),
        },
    }
    return render(request, 'expt_webapp/materials/detail.html', ctx)


def material_create(request):
    if request.method == 'POST':
        mat = Material.objects.create(
            material_type_id=request.POST['material_type'],
            name=request.POST['name'],
            version=request.POST['version'],
            description=request.POST.get('description') or None,
            link=request.POST.get('link') or None,
        )
        messages.success(request, f'Material "{mat.name}" created.')
        return redirect('material-detail', pk=mat.pk)
    return render(request, 'expt_webapp/materials/form.html', {
        'material_types': MaterialType.objects.all().order_by('name'),
    })


def material_edit(request, pk):
    material = get_object_or_404(Material, pk=pk)
    if request.method == 'POST':
        material.material_type_id = request.POST['material_type']
        material.name             = request.POST['name']
        material.version          = request.POST['version']
        material.description      = request.POST.get('description') or None
        material.link             = request.POST.get('link') or None
        material.save()
        messages.success(request, 'Material updated.')
        return redirect('material-detail', pk=material.pk)
    return render(request, 'expt_webapp/materials/form.html', {
        'material':       material,
        'material_types': MaterialType.objects.all().order_by('name'),
    })


# =============================================================================
# SETUPS
# =============================================================================

def setup_list(request):
    qs = Setup.objects.annotate(
        platform_count=Count('setupplatform'),
        run_count=Count('run'),
    ).order_by('-created_at')
    return render(request, 'expt_webapp/setups/list.html', {'setups': qs})


def setup_detail(request, pk):
    setup = get_object_or_404(Setup, pk=pk)
    platforms = SetupPlatform.objects.filter(setup=setup).select_related('platform')
    runs = Run.objects.filter(setup=setup).select_related('experiment').order_by('-created_at')[:20]
    return render(request, 'expt_webapp/setups/detail.html', {
        'setup':     setup,
        'platforms': platforms,
        'runs':      runs,
    })


def setup_create(request):
    if request.method == 'POST':
        setup = Setup.objects.create(
            name=request.POST['name'],
            description=request.POST.get('description') or None,
        )
        platform_ids = request.POST.getlist('platforms')
        for pid in platform_ids:
            role = request.POST.get(f'platform_role_{pid}') or None
            SetupPlatform.objects.get_or_create(setup=setup, platform_id=pid, defaults={'role': role})
        messages.success(request, f'Setup "{setup.name}" created.')
        return redirect('setup-detail', pk=setup.pk)
    return render(request, 'expt_webapp/setups/form.html', {
        'all_platforms': Platform.objects.all().order_by('name'),
    })


def setup_edit(request, pk):
    setup = get_object_or_404(Setup, pk=pk)
    if request.method == 'POST':
        setup.name        = request.POST['name']
        setup.description = request.POST.get('description') or None
        setup.save()
        platform_ids = request.POST.getlist('platforms')
        SetupPlatform.objects.filter(setup=setup).delete()
        for pid in platform_ids:
            role = request.POST.get(f'platform_role_{pid}') or None
            SetupPlatform.objects.create(setup=setup, platform_id=pid, role=role)
        messages.success(request, 'Setup updated.')
        return redirect('setup-detail', pk=setup.pk)
    current_platform_ids = list(SetupPlatform.objects.filter(setup=setup).values_list('platform_id', flat=True))
    current_roles = {sp.platform_id: sp.role for sp in SetupPlatform.objects.filter(setup=setup)}
    return render(request, 'expt_webapp/setups/form.html', {
        'setup': setup,
        'all_platforms': Platform.objects.all().order_by('name'),
        'current_platform_ids': current_platform_ids,
        'current_roles': current_roles,
    })


# =============================================================================
# PLATFORMS
# =============================================================================

def platform_list(request):
    qs = Platform.objects.annotate(
        setup_count=Count('setupplatform')
    ).order_by('-created_at')
    return render(request, 'expt_webapp/platforms/list.html', {'platforms': qs})


def platform_detail(request, pk):
    platform = get_object_or_404(Platform, pk=pk)
    setups = SetupPlatform.objects.filter(platform=platform).select_related('setup')
    setup_ids = setups.values_list('setup_id', flat=True)
    runs = Run.objects.filter(setup_id__in=setup_ids).select_related('experiment').order_by('-created_at')[:20]
    return render(request, 'expt_webapp/platforms/detail.html', {
        'platform': platform,
        'setups':   setups,
        'runs':     runs,
    })


def platform_create(request):
    if request.method == 'POST':
        p = Platform.objects.create(
            name=request.POST['name'],
            description=request.POST.get('description') or None,
        )
        setup_ids = request.POST.getlist('setups')
        for sid in setup_ids:
            role = request.POST.get(f'setup_role_{sid}') or None
            SetupPlatform.objects.get_or_create(setup_id=sid, platform=p, defaults={'role': role})
        messages.success(request, f'Platform "{p.name}" created.')
        return redirect('platform-detail', pk=p.pk)
    return render(request, 'expt_webapp/platforms/form.html', {
        'all_setups': Setup.objects.all().order_by('name'),
    })


def platform_edit(request, pk):
    platform = get_object_or_404(Platform, pk=pk)
    if request.method == 'POST':
        platform.name        = request.POST['name']
        platform.description = request.POST.get('description') or None
        platform.save()
        setup_ids = request.POST.getlist('setups')
        SetupPlatform.objects.filter(platform=platform).delete()
        for sid in setup_ids:
            role = request.POST.get(f'setup_role_{sid}') or None
            SetupPlatform.objects.create(setup_id=sid, platform=platform, role=role)
        messages.success(request, 'Platform updated.')
        return redirect('platform-detail', pk=platform.pk)
    current_setup_ids = list(SetupPlatform.objects.filter(platform=platform).values_list('setup_id', flat=True))
    current_roles = {sp.setup_id: sp.role for sp in SetupPlatform.objects.filter(platform=platform)}
    return render(request, 'expt_webapp/platforms/form.html', {
        'platform': platform,
        'all_setups': Setup.objects.all().order_by('name'),
        'current_setup_ids': current_setup_ids,
        'current_roles': current_roles,
    })


# =============================================================================
# TAGS
# =============================================================================

def tag_list(request):
    tags = Tag.objects.annotate(entity_count=Count('entitytag')).order_by('name')
    return render(request, 'expt_webapp/tags/list.html', {'tags': tags})


def tag_detail(request, pk):
    tag = get_object_or_404(Tag, pk=pk)
    entity_tags = EntityTag.objects.filter(tag=tag)
    return render(request, 'expt_webapp/tags/detail.html', {
        'tag':          tag,
        'entity_tags':  entity_tags,
        'entity_count': entity_tags.count(),
    })


def tag_create(request):
    if request.method == 'POST':
        tag = Tag.objects.create(
            name=request.POST['name'],
            color=request.POST.get('color') or '#c8ff00',
        )
        messages.success(request, f'Tag "{tag.name}" created.')
        return redirect('tag-detail', pk=tag.pk)
    return render(request, 'expt_webapp/tags/form.html', {})


def tag_edit(request, pk):
    tag = get_object_or_404(Tag, pk=pk)
    if request.method == 'POST':
        tag.name  = request.POST['name']
        tag.color = request.POST.get('color') or '#c8ff00'
        tag.save()
        messages.success(request, 'Tag updated.')
        return redirect('tag-detail', pk=tag.pk)
    return render(request, 'expt_webapp/tags/form.html', {'tag': tag})



# =============================================================================
# MATERIAL TYPES
# =============================================================================

def material_type_list(request):
    types = MaterialType.objects.annotate(
        material_count=Count('material')
    ).order_by('name')
    return render(request, 'expt_webapp/material_types/list.html', {'material_types': types})


def material_type_detail(request, pk):
    mt = get_object_or_404(MaterialType, pk=pk)
    materials = Material.objects.filter(material_type=mt).order_by('-created_at')
    return render(request, 'expt_webapp/material_types/detail.html', {
        'material_type': mt,
        'materials': materials,
    })


def material_type_create(request):
    if request.method == 'POST':
        mt = MaterialType.objects.create(
            name=request.POST['name'],
            description=request.POST.get('description') or None,
        )
        messages.success(request, f'Material Type "{mt.name}" created.')
        return redirect('material-type-detail', pk=mt.pk)
    return render(request, 'expt_webapp/material_types/form.html', {})


def material_type_edit(request, pk):
    mt = get_object_or_404(MaterialType, pk=pk)
    if request.method == 'POST':
        mt.name        = request.POST['name']
        mt.description = request.POST.get('description') or None
        mt.save()
        messages.success(request, 'Material Type updated.')
        return redirect('material-type-detail', pk=mt.pk)
    return render(request, 'expt_webapp/material_types/form.html', {'material_type': mt})


# =============================================================================
# SEARCH
# =============================================================================

def search(request):
    query = request.GET.get('q', '').strip()
    results = {}
    if query:
        results['models'] = Model.objects.filter(
            Q(name__icontains=query) | Q(description__icontains=query)
        )
        results['experiments'] = Experiment.objects.select_related('model').filter(
            Q(name__icontains=query) | Q(description__icontains=query)
        )
        results['runs'] = Run.objects.select_related('experiment').filter(
            Q(name__icontains=query) | Q(notes__icontains=query)
        )
        results['materials'] = Material.objects.select_related('material_type').filter(
            Q(name__icontains=query) | Q(description__icontains=query)
        )
        results['tags'] = Tag.objects.filter(name__icontains=query)
    return render(request, 'expt_webapp/search.html', {
        'query':   query,
        'results': results,
    })