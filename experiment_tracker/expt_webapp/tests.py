from itertools import count
from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APITestCase, APIClient
from rest_framework import status

from .models import (
    Model, Experiment, Run, Setup, Platform,
    SetupPlatform, ExperimentMaterial, ModelMaterial,
    MaterialType, Material, Parameter, RunMetric,
    RunOutput, RunLog, Tag, EntityTag,
)


# =============================================================================
# FACTORIES — lightweight helpers to create test data
# Each factory uses a thread-safe counter so names are always unique,
# preventing unique_together collisions across tests in the same class.
# =============================================================================

_counters = {k: count(1) for k in ('model', 'experiment', 'setup', 'run', 'platform', 'material_type', 'material', 'tag')}

def _n(key):
    """Return the next integer for the given counter key."""
    return next(_counters[key])


def make_model(**kwargs):
    n = _n('model')
    defaults = {'name': f'TestModel-{n}', 'version': 'v1', 'description': 'A test model'}
    defaults.update(kwargs)
    return Model.objects.create(**defaults)


def make_experiment(model=None, **kwargs):
    if model is None:
        model = make_model()
    n = _n('experiment')
    defaults = {'model': model, 'name': f'TestExperiment-{n}', 'version': 'v1', 'type': 'classification'}
    defaults.update(kwargs)
    return Experiment.objects.create(**defaults)


def make_setup(**kwargs):
    n = _n('setup')
    defaults = {'name': f'TestSetup-{n}', 'description': 'A test setup'}
    defaults.update(kwargs)
    return Setup.objects.create(**defaults)


def make_run(experiment=None, setup=None, **kwargs):
    if experiment is None:
        experiment = make_experiment()
    if setup is None:
        setup = make_setup()
    n = _n('run')
    defaults = {'experiment': experiment, 'setup': setup, 'status': 'pending', 'name': f'TestRun-{n}'}
    defaults.update(kwargs)
    return Run.objects.create(**defaults)


def make_platform(**kwargs):
    n = _n('platform')
    defaults = {'name': f'TestPlatform-{n}', 'description': 'A test platform'}
    defaults.update(kwargs)
    return Platform.objects.create(**defaults)


def make_material_type(**kwargs):
    n = _n('material_type')
    defaults = {'name': f'dataset-{n}', 'description': 'A dataset type'}
    defaults.update(kwargs)
    return MaterialType.objects.create(**defaults)


def make_material(material_type=None, **kwargs):
    if material_type is None:
        material_type = make_material_type()
    n = _n('material')
    defaults = {'material_type': material_type, 'name': f'TestMaterial-{n}', 'version': 'v1'}
    defaults.update(kwargs)
    return Material.objects.create(**defaults)


def make_tag(**kwargs):
    n = _n('tag')
    defaults = {'name': f'test-tag-{n}', 'color': '#FF0000'}
    defaults.update(kwargs)
    return Tag.objects.create(**defaults)


# =============================================================================
# MODEL TESTS
# =============================================================================

class ModelModelTests(TestCase):

    def test_create_model(self):
        m = make_model(name='GPT', version='v2')
        self.assertEqual(m.name, 'GPT')
        self.assertEqual(m.version, 'v2')
        self.assertIsNotNone(m.created_at)

    def test_unique_together_name_version(self):
        make_model(name='GPT', version='v1')
        from django.db import IntegrityError
        with self.assertRaises(IntegrityError):
            make_model(name='GPT', version='v1')

    def test_parent_model_self_reference(self):
        parent = make_model(name='BaseModel', version='v1')
        child = make_model(name='FineTuned', version='v1', parent_model=parent)
        self.assertEqual(child.parent_model, parent)

    def test_parent_set_null_on_delete(self):
        parent = make_model(name='ParentModel', version='v1')
        child = make_model(name='ChildModel', version='v1', parent_model=parent)
        parent.delete()
        child.refresh_from_db()
        self.assertIsNone(child.parent_model)


class ExperimentModelTests(TestCase):

    def test_create_experiment(self):
        exp = make_experiment(name='Exp1', version='v1')
        self.assertEqual(exp.name, 'Exp1')
        self.assertIsNotNone(exp.model)

    def test_unique_together_model_name_version(self):
        model = make_model()
        make_experiment(model=model, name='Exp', version='v1')
        from django.db import IntegrityError
        with self.assertRaises(IntegrityError):
            make_experiment(model=model, name='Exp', version='v1')

    def test_cascade_delete_with_model(self):
        exp = make_experiment()
        model_id = exp.model.id
        exp.model.delete()
        self.assertFalse(Experiment.objects.filter(id=exp.id).exists())


class RunModelTests(TestCase):

    def test_create_run(self):
        run = make_run(status='running')
        self.assertEqual(run.status, 'running')

    def test_status_choices(self):
        for s in ['pending', 'running', 'successful', 'failed', 'cancelled']:
            run = make_run(
                experiment=make_experiment(name=f'Exp-{s}', version='v1'),
                status=s
            )
            self.assertEqual(run.status, s)

    def test_cascade_delete_with_experiment(self):
        run = make_run()
        run.experiment.delete()
        self.assertFalse(Run.objects.filter(id=run.id).exists())


class MaterialModelTests(TestCase):

    def test_create_material(self):
        m = make_material(name='ImageNet', version='v2')
        self.assertEqual(m.name, 'ImageNet')

    def test_unique_together_name_version(self):
        make_material(name='Dataset', version='v1')
        from django.db import IntegrityError
        with self.assertRaises(IntegrityError):
            make_material(name='Dataset', version='v1')


# =============================================================================
# MODEL VIEWSET API TESTS
# =============================================================================

class ModelViewSetTests(APITestCase):

    def setUp(self):
        self.client = APIClient()

    def test_list_models(self):
        make_model(name='M1', version='v1')
        make_model(name='M2', version='v1')
        response = self.client.get('/api/models/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertGreaterEqual(len(response.data['results']), 2)

    def test_create_model(self):
        data = {'name': 'NewModel', 'version': 'v1', 'description': 'Test'}
        response = self.client.post('/api/models/', data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['name'], 'NewModel')

    def test_retrieve_model(self):
        m = make_model()
        response = self.client.get(f'/api/models/{m.id}/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['id'], m.id)

    def test_update_model(self):
        m = make_model()
        response = self.client.patch(f'/api/models/{m.id}/', {'description': 'Updated'}, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['description'], 'Updated')

    def test_delete_model(self):
        m = make_model()
        response = self.client.delete(f'/api/models/{m.id}/')
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Model.objects.filter(id=m.id).exists())

    def test_model_experiments_action(self):
        m = make_model()
        make_experiment(model=m, name='Exp1', version='v1')
        make_experiment(model=m, name='Exp2', version='v1')
        response = self.client.get(f'/api/models/{m.id}/experiments/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 2)

    def test_model_lineage_action(self):
        parent = make_model(name='Parent', version='v1')
        child = make_model(name='Child', version='v1', parent_model=parent)
        response = self.client.get(f'/api/models/{child.id}/lineage/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['ancestors'][0]['id'], parent.id)

    def test_model_stats_action(self):
        m = make_model()
        exp = make_experiment(model=m)
        make_run(experiment=exp, status='successful')
        make_run(experiment=exp, status='failed')
        response = self.client.get(f'/api/models/{m.id}/stats/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['total_runs'], 2)
        self.assertEqual(response.data['total_experiments'], 1)

    def test_model_materials_action(self):
        m = make_model()
        mat = make_material()
        ModelMaterial.objects.create(model=m, material=mat, relation_type='training_data')
        response = self.client.get(f'/api/models/{m.id}/materials/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['relation_type'], 'training_data')

    def test_filter_by_name(self):
        make_model(name='AlphaNet', version='v1')
        make_model(name='BetaNet', version='v1')
        response = self.client.get('/api/models/?name=Alpha')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        names = [r['name'] for r in response.data['results']]
        self.assertIn('AlphaNet', names)
        self.assertNotIn('BetaNet', names)


# =============================================================================
# EXPERIMENT VIEWSET API TESTS
# =============================================================================

class ExperimentViewSetTests(APITestCase):

    def setUp(self):
        self.model = make_model()

    def test_list_experiments(self):
        make_experiment(model=self.model, name='E1', version='v1')
        response = self.client.get('/api/experiments/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_create_experiment(self):
        data = {'model': self.model.id, 'name': 'NewExp', 'version': 'v1', 'type': 'regression'}
        response = self.client.post('/api/experiments/', data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_experiment_runs_action(self):
        exp = make_experiment(model=self.model)
        make_run(experiment=exp, status='successful')
        make_run(experiment=exp, status='failed')
        response = self.client.get(f'/api/experiments/{exp.id}/runs/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 2)

    def test_experiment_runs_filter_by_status(self):
        exp = make_experiment(model=self.model)
        make_run(experiment=exp, status='successful')
        make_run(experiment=exp, status='failed')
        response = self.client.get(f'/api/experiments/{exp.id}/runs/?status=successful')
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['status'], 'successful')

    def test_experiment_summary_action(self):
        exp = make_experiment(model=self.model)
        run = make_run(experiment=exp, status='successful')
        RunMetric.objects.create(run=run, metric_name='accuracy', metric_value=0.95)
        response = self.client.get(f'/api/experiments/{exp.id}/summary/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['total_runs'], 1)
        self.assertEqual(len(response.data['metric_aggregates']), 1)

    def test_experiment_materials_action(self):
        exp = make_experiment(model=self.model)
        mat = make_material()
        ExperimentMaterial.objects.create(experiment=exp, material=mat, role='training')
        response = self.client.get(f'/api/experiments/{exp.id}/materials/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data[0]['role'], 'training')

    def test_filter_by_model_id(self):
        other_model = make_model(name='OtherModel', version='v1')
        make_experiment(model=self.model, name='E1', version='v1')
        make_experiment(model=other_model, name='E2', version='v1')
        response = self.client.get(f'/api/experiments/?model_id={self.model.id}')
        self.assertEqual(len(response.data['results']), 1)


# =============================================================================
# RUN VIEWSET API TESTS
# =============================================================================

class RunViewSetTests(APITestCase):

    def setUp(self):
        self.experiment = make_experiment()
        self.setup = make_setup()

    def test_create_run(self):
        data = {
            'experiment': self.experiment.id,
            'setup': self.setup.id,
            'status': 'pending',
            'name': 'Run1',
        }
        response = self.client.post('/api/runs/', data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_run_logs_action(self):
        run = make_run(experiment=self.experiment, setup=self.setup)
        RunLog.objects.create(run=run, level='info', message='Started')
        RunLog.objects.create(run=run, level='error', message='Something failed')
        response = self.client.get(f'/api/runs/{run.id}/logs/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 2)

    def test_run_logs_filter_by_level(self):
        run = make_run(experiment=self.experiment, setup=self.setup)
        RunLog.objects.create(run=run, level='info', message='Info msg')
        RunLog.objects.create(run=run, level='warning', message='Warning msg')
        response = self.client.get(f'/api/runs/{run.id}/logs/?level=info')
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['level'], 'info')

    def test_run_metrics_action(self):
        run = make_run(experiment=self.experiment, setup=self.setup)
        RunMetric.objects.create(run=run, metric_name='loss', metric_value=0.25)
        RunMetric.objects.create(run=run, metric_name='accuracy', metric_value=0.91)
        response = self.client.get(f'/api/runs/{run.id}/metrics/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 2)

    def test_run_outputs_action(self):
        run = make_run(experiment=self.experiment, setup=self.setup)
        RunOutput.objects.create(run=run, type='result', name='final_score', value='0.95')
        response = self.client.get(f'/api/runs/{run.id}/outputs/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)

    def test_run_timeline_action(self):
        run = make_run(experiment=self.experiment, setup=self.setup)
        RunLog.objects.create(run=run, level='info', message='Started')
        RunOutput.objects.create(run=run, type='artifact', name='checkpoint')
        response = self.client.get(f'/api/runs/{run.id}/timeline/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['events']), 2)

    def test_run_summary_action(self):
        run = make_run(experiment=self.experiment, setup=self.setup,
                       started_at=timezone.now(), finished_at=timezone.now())
        RunLog.objects.create(run=run, level='error', message='Oops')
        RunMetric.objects.create(run=run, metric_name='f1', metric_value=0.88)
        response = self.client.get(f'/api/runs/{run.id}/summary/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['log_counts']['error'], 1)
        self.assertEqual(len(response.data['metrics']), 1)

    def test_compare_metrics_action(self):
        run1 = make_run(experiment=self.experiment, setup=self.setup, name='R1')
        run2 = make_run(
            experiment=make_experiment(name='Exp2', version='v1'),
            setup=self.setup,
            name='R2'
        )
        RunMetric.objects.create(run=run1, metric_name='accuracy', metric_value=0.90)
        RunMetric.objects.create(run=run2, metric_name='accuracy', metric_value=0.85)
        response = self.client.post(
            '/api/runs/compare_metrics/',
            {'run_ids': [run1.id, run2.id]},
            format='json'
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn(run1.id, response.data)
        self.assertIn(run2.id, response.data)

    def test_compare_metrics_missing_run_ids(self):
        response = self.client.post('/api/runs/compare_metrics/', {}, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_filter_by_status(self):
        make_run(experiment=self.experiment, setup=self.setup, status='successful')
        make_run(experiment=self.experiment, setup=self.setup, status='failed')
        response = self.client.get('/api/runs/?status=successful')
        for r in response.data['results']:
            self.assertEqual(r['status'], 'successful')


# =============================================================================
# SETUP VIEWSET API TESTS
# =============================================================================

class SetupViewSetTests(APITestCase):

    def test_create_and_list_setup(self):
        data = {'name': 'GPU Setup', 'description': 'NVIDIA A100'}
        response = self.client.post('/api/setups/', data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        response = self.client.get('/api/setups/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_setup_platforms_action(self):
        setup = make_setup()
        platform = make_platform()
        SetupPlatform.objects.create(setup=setup, platform=platform, role='primary', config={'gpu': 'A100'})
        response = self.client.get(f'/api/setups/{setup.id}/platforms/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['role'], 'primary')

    def test_setup_runs_action(self):
        setup = make_setup()
        make_run(setup=setup)
        make_run(setup=setup)
        response = self.client.get(f'/api/setups/{setup.id}/runs/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 2)

    def test_setup_config_action(self):
        setup = make_setup()
        platform = make_platform()
        SetupPlatform.objects.create(setup=setup, platform=platform, config={'memory': '80GB'})
        response = self.client.get(f'/api/setups/{setup.id}/config/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn(platform.name, response.data['platform_configs'])


# =============================================================================
# PLATFORM VIEWSET API TESTS
# =============================================================================

class PlatformViewSetTests(APITestCase):

    def test_create_and_list_platform(self):
        data = {'name': 'AWS-p4d', 'description': 'EC2 p4d instance'}
        response = self.client.post('/api/platforms/', data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_platform_setups_action(self):
        platform = make_platform()
        setup = make_setup()
        SetupPlatform.objects.create(setup=setup, platform=platform, role='gpu')
        response = self.client.get(f'/api/platforms/{platform.id}/setups/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)

    def test_platform_runs_action(self):
        platform = make_platform()
        setup = make_setup()
        SetupPlatform.objects.create(setup=setup, platform=platform)
        make_run(setup=setup)
        response = self.client.get(f'/api/platforms/{platform.id}/runs/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertGreaterEqual(len(response.data), 1)


# =============================================================================
# MATERIAL VIEWSET API TESTS
# =============================================================================

class MaterialViewSetTests(APITestCase):

    def test_create_and_list_material(self):
        mt = make_material_type()
        data = {'material_type': mt.id, 'name': 'CIFAR-10', 'version': 'v1'}
        response = self.client.post('/api/materials/', data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_material_models_action(self):
        mat = make_material()
        m = make_model()
        ModelMaterial.objects.create(model=m, material=mat, relation_type='eval')
        response = self.client.get(f'/api/materials/{mat.id}/models/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)

    def test_material_experiments_action(self):
        mat = make_material()
        exp = make_experiment()
        ExperimentMaterial.objects.create(experiment=exp, material=mat, role='test')
        response = self.client.get(f'/api/materials/{mat.id}/experiments/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)

    def test_material_usage_action(self):
        mat = make_material()
        m = make_model()
        exp = make_experiment()
        ModelMaterial.objects.create(model=m, material=mat)
        ExperimentMaterial.objects.create(experiment=exp, material=mat)
        response = self.client.get(f'/api/materials/{mat.id}/usage/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['used_in_models'], 1)
        self.assertEqual(response.data['used_in_experiments'], 1)


# =============================================================================
# PARAMETER VIEWSET API TESTS
# =============================================================================

class ParameterViewSetTests(APITestCase):

    def test_create_and_list_parameter(self):
        run = make_run()
        data = {'entity_type': 'run', 'entity_id': run.id, 'key': 'learning_rate', 'value': '0.001', 'value_type': 'float'}
        response = self.client.post('/api/parameters/', data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_filter_by_entity(self):
        run = make_run()
        Parameter.objects.create(entity_type='run', entity_id=run.id, key='lr', value='0.01')
        Parameter.objects.create(entity_type='model', entity_id=1, key='layers', value='12')
        response = self.client.get('/api/parameters/?entity_type=run')
        for p in response.data['results']:
            self.assertEqual(p['entity_type'], 'run')

    def test_bulk_update_action(self):
        run = make_run()
        payload = [
            {'entity_type': 'run', 'entity_id': run.id, 'key': 'lr', 'value': '0.001', 'value_type': 'float'},
            {'entity_type': 'run', 'entity_id': run.id, 'key': 'epochs', 'value': '10', 'value_type': 'int'},
        ]
        response = self.client.post('/api/parameters/bulk_update/', payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 2)

    def test_search_action(self):
        run = make_run()
        Parameter.objects.create(entity_type='run', entity_id=run.id, key='dropout_rate', value='0.3')
        response = self.client.get('/api/parameters/search/?q=dropout')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertGreaterEqual(len(response.data), 1)

    def test_bulk_update_requires_list(self):
        response = self.client.post('/api/parameters/bulk_update/', {'key': 'lr'}, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


# =============================================================================
# TAG VIEWSET API TESTS
# =============================================================================

class TagViewSetTests(APITestCase):

    def test_create_and_list_tag(self):
        data = {'name': 'production', 'color': '#00FF00'}
        response = self.client.post('/api/tags/', data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_assign_tag_action(self):
        tag = make_tag()
        run = make_run()
        response = self.client.post(
            f'/api/tags/{tag.id}/assign/',
            {'entity_type': 'run', 'entity_id': run.id},
            format='json'
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(EntityTag.objects.filter(tag=tag, entity_type='run', entity_id=run.id).exists())

    def test_assign_tag_idempotent(self):
        tag = make_tag()
        run = make_run()
        self.client.post(f'/api/tags/{tag.id}/assign/', {'entity_type': 'run', 'entity_id': run.id}, format='json')
        response = self.client.post(f'/api/tags/{tag.id}/assign/', {'entity_type': 'run', 'entity_id': run.id}, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(EntityTag.objects.filter(tag=tag).count(), 1)

    def test_remove_tag_action(self):
        tag = make_tag()
        run = make_run()
        EntityTag.objects.create(tag=tag, entity_type='run', entity_id=run.id)
        response = self.client.post(
            f'/api/tags/{tag.id}/remove/',
            {'entity_type': 'run', 'entity_id': run.id},
            format='json'
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertFalse(EntityTag.objects.filter(tag=tag).exists())

    def test_remove_nonexistent_tag(self):
        tag = make_tag()
        response = self.client.post(
            f'/api/tags/{tag.id}/remove/',
            {'entity_type': 'run', 'entity_id': 9999},
            format='json'
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_entities_action(self):
        tag = make_tag()
        run = make_run()
        EntityTag.objects.create(tag=tag, entity_type='run', entity_id=run.id)
        response = self.client.get(f'/api/tags/{tag.id}/entities/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)

    def test_assign_missing_fields(self):
        tag = make_tag()
        response = self.client.post(f'/api/tags/{tag.id}/assign/', {}, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


# =============================================================================
# RUN LOG / METRIC / OUTPUT VIEWSET TESTS
# =============================================================================

class RunLogViewSetTests(APITestCase):

    def test_create_and_list_log(self):
        run = make_run()
        data = {'run': run.id, 'level': 'info', 'message': 'Training started'}
        response = self.client.post('/api/run-logs/', data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_filter_by_run_id(self):
        run1 = make_run()
        run2 = make_run(experiment=make_experiment(name='E2', version='v1'))
        RunLog.objects.create(run=run1, level='info', message='Run 1 log')
        RunLog.objects.create(run=run2, level='info', message='Run 2 log')
        response = self.client.get(f'/api/run-logs/?run_id={run1.id}')
        for log in response.data['results']:
            self.assertEqual(log['run'], run1.id)


class RunMetricViewSetTests(APITestCase):

    def test_create_metric(self):
        run = make_run()
        data = {'run': run.id, 'metric_name': 'precision', 'metric_value': 0.88}
        response = self.client.post('/api/run-metrics/', data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_aggregate_action(self):
        exp = make_experiment()
        run1 = make_run(experiment=exp, setup=make_setup(name='S2'))
        run2 = make_run(experiment=exp, setup=make_setup(name='S3'))
        RunMetric.objects.create(run=run1, metric_name='f1', metric_value=0.80)
        RunMetric.objects.create(run=run2, metric_name='f1', metric_value=0.90)
        response = self.client.get(f'/api/run-metrics/aggregate/?experiment_id={exp.id}&metric_name=f1')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertAlmostEqual(response.data['avg'], 0.85)

    def test_aggregate_missing_params(self):
        response = self.client.get('/api/run-metrics/aggregate/')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


class RunOutputViewSetTests(APITestCase):

    def test_create_output(self):
        run = make_run()
        data = {'run': run.id, 'type': 'result', 'name': 'score', 'value': '0.92'}
        response = self.client.post('/api/run-outputs/', data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_filter_by_type(self):
        run = make_run()
        RunOutput.objects.create(run=run, type='file', name='weights.h5')
        RunOutput.objects.create(run=run, type='result', name='score', value='0.9')
        response = self.client.get(f'/api/run-outputs/?run_id={run.id}&type=file')
        for o in response.data['results']:
            self.assertEqual(o['type'], 'file')


# =============================================================================
# SEARCH VIEW TESTS
# =============================================================================

class SearchViewTests(APITestCase):

    def test_search_returns_all_entity_types(self):
        make_model(name='SearchableModel', version='v1')
        response = self.client.get('/api/search/?q=Searchable')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('models', response.data)
        self.assertIn('experiments', response.data)
        self.assertIn('runs', response.data)
        self.assertIn('materials', response.data)
        self.assertIn('tags', response.data)

    def test_search_filter_by_entity_type(self):
        make_model(name='FilterModel', version='v1')
        response = self.client.get('/api/search/?q=Filter&entity=models')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('models', response.data)
        self.assertNotIn('runs', response.data)

    def test_empty_query_returns_results(self):
        response = self.client.get('/api/search/?q=')
        self.assertEqual(response.status_code, status.HTTP_200_OK)


# =============================================================================
# DASHBOARD VIEWSET TESTS
# =============================================================================

class DashboardViewSetTests(APITestCase):

    def test_global_overview(self):
        make_run(status='successful')
        make_run(status='failed')
        response = self.client.get('/api/dashboard/global_overview/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('total_models', response.data)
        self.assertIn('total_runs', response.data)
        self.assertIn('success_rate', response.data)

    def test_model_dashboard(self):
        m = make_model()
        exp = make_experiment(model=m)
        make_run(experiment=exp, status='successful')
        response = self.client.get(f'/api/dashboard/model/?model_id={m.id}')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['experiment_count'], 1)

    def test_model_dashboard_missing_id(self):
        response = self.client.get('/api/dashboard/model/')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_model_dashboard_not_found(self):
        response = self.client.get('/api/dashboard/model/?model_id=99999')
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_experiment_dashboard(self):
        exp = make_experiment()
        make_run(experiment=exp, status='successful')
        response = self.client.get(f'/api/dashboard/experiment/?experiment_id={exp.id}')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('success_rate', response.data)

    def test_run_dashboard(self):
        run = make_run(started_at=timezone.now(), finished_at=timezone.now())
        RunMetric.objects.create(run=run, metric_name='acc', metric_value=0.9)
        RunLog.objects.create(run=run, level='info', message='done')
        response = self.client.get(f'/api/dashboard/run/?run_id={run.id}')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('log_distribution', response.data)
        self.assertIn('duration_seconds', response.data)


# =============================================================================
# GRAPH VIEWSET TESTS
# =============================================================================

class GraphViewSetTests(APITestCase):

    def test_model_graph(self):
        parent = make_model(name='ParentGraph', version='v1')
        child = make_model(name='ChildGraph', version='v1', parent_model=parent)
        make_experiment(model=child)
        response = self.client.get(f'/api/graph/model/?model_id={child.id}')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('parent', response.data)
        self.assertIn('children', response.data)
        self.assertIn('experiments', response.data)

    def test_experiment_graph(self):
        exp = make_experiment()
        setup = make_setup(name='GraphSetup')
        platform = make_platform(name='GraphPlatform')
        SetupPlatform.objects.create(setup=setup, platform=platform)
        make_run(experiment=exp, setup=setup)
        response = self.client.get(f'/api/graph/experiment/?experiment_id={exp.id}')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('platform_distribution', response.data)

    def test_model_graph_missing_id(self):
        response = self.client.get('/api/graph/model/')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


# =============================================================================
# ACTIVITY VIEW TESTS
# =============================================================================

class ActivityViewTests(APITestCase):

    def test_activity_feed(self):
        make_model()
        make_run(status='failed', finished_at=timezone.now())
        response = self.client.get('/api/activity/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('recent_models', response.data)
        self.assertIn('recent_failures', response.data)
        self.assertIn('active_runs', response.data)

    def test_activity_limit(self):
        for i in range(5):
            make_model(name=f'Model{i}', version='v1')
        response = self.client.get('/api/activity/?limit=3')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertLessEqual(len(response.data['recent_models']), 3)


# =============================================================================
# MODEL COMPARISON VIEW TESTS
# =============================================================================

class ModelComparisonViewTests(APITestCase):

    def test_compare_models(self):
        m1 = make_model(name='ModelA', version='v1')
        m2 = make_model(name='ModelB', version='v1')
        exp1 = make_experiment(model=m1)
        exp2 = make_experiment(model=m2)
        run1 = make_run(experiment=exp1, status='successful')
        run2 = make_run(experiment=exp2, status='failed')
        RunMetric.objects.create(run=run1, metric_name='acc', metric_value=0.95)
        RunMetric.objects.create(run=run2, metric_name='acc', metric_value=0.70)
        response = self.client.post(
            '/api/compare/models/',
            {'model_ids': [m1.id, m2.id]},
            format='json'
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 2)

    def test_compare_requires_two_models(self):
        m = make_model()
        response = self.client.post('/api/compare/models/', {'model_ids': [m.id]}, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


# =============================================================================
# VERSION TRACKING VIEW TESTS
# =============================================================================

class VersionTrackingViewTests(APITestCase):

    def test_model_version_history(self):
        Model.objects.create(name='VersionedModel', version='v1')
        Model.objects.create(name='VersionedModel', version='v2')
        response = self.client.get('/api/versions/?entity=model&name=VersionedModel')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 2)

    def test_material_version_history(self):
        mt = make_material_type()
        Material.objects.create(material_type=mt, name='VersionedDataset', version='v1')
        Material.objects.create(material_type=mt, name='VersionedDataset', version='v2')
        response = self.client.get('/api/versions/?entity=material&name=VersionedDataset')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 2)

    def test_invalid_entity_type(self):
        response = self.client.get('/api/versions/?entity=unknown&name=Test')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_missing_params(self):
        response = self.client.get('/api/versions/')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)