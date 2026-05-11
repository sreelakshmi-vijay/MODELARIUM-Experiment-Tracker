from django.db import models # Provides base classes for defining database models (tables) in Django

# Create your models here.

# This file is where you define your database models (tables) using Django's ORM.


# =============================================================================
# DATABASE MODELS USED IN THIS PROJECT ARE AS FOLLOWS:
# =============================================================================


# -----------------------------------------------------------------------------
# CORE ENTITIES
# -----------------------------------------------------------------------------


# 1. MODELS:
# -----------------------------------------------------------------------------
# This model represents the experimental models used in an experiment.
# Each model is versioned and can optionally reference a parent model
# to support lineage (e.g., fine-tuned or derived models).
#
# Schema:
#   id (PK)
#   name (NOT NULL)
#   description
#   version (NOT NULL)
#   parent_model_id (FK → models.id)
#   created_at (NOT NULL)
#
# Constraints:
#   UNIQUE (name, version)

class Model(models.Model):
    id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=255, null=False)
    description = models.TextField(null=True)
    version = models.CharField(max_length=50, null=False)
    parent_model = models.ForeignKey('self', on_delete=models.SET_NULL, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = (('name', 'version'),)


# 2. EXPERIMENTS:
# -----------------------------------------------------------------------------
# Represents experiments conducted on models.
# Each experiment is tied to a specific model and is versioned.
#
# Schema:
#   id (PK)
#   model_id (FK → models.id, NOT NULL)
#   name (NOT NULL)
#   type
#   version (NOT NULL)
#   description
#   created_at (NOT NULL)
#
# Constraints:
#   UNIQUE (model_id, name, version)

class Experiment(models.Model):
    id = models.AutoField(primary_key=True)
    model = models.ForeignKey(Model, on_delete=models.CASCADE)
    name = models.CharField(max_length=255, null=False)
    type = models.CharField(max_length=100, null=True)
    version = models.CharField(max_length=50, null=False)
    description = models.TextField(null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = (('model', 'name', 'version'),)

# 3. RUNS:
# -----------------------------------------------------------------------------
# Represents execution instances of experiments using a setup.
# Tracks lifecycle status and timestamps.
#
# Schema:
#   id (PK)
#   experiment_id (FK → experiments.id, NOT NULL)
#   setup_id (FK → setups.id, NOT NULL)
#   name
#   status (NOT NULL)
#   started_at
#   finished_at
#   created_at (NOT NULL)
#   notes
#
# Constraints:
#   CHECK status IN ('pending','running','completed','failed','cancelled')
#
# Indexes:
#   INDEX (experiment_id)
#   INDEX (setup_id)

class Run(models.Model):

    STATUS_CHOICES = [
    ('pending', 'Pending'),
    ('running', 'Running'),
    ('successful', 'Successful'),
    ('failed', 'Failed'),
    ('cancelled', 'Cancelled'),
]

    id = models.AutoField(primary_key=True)
    experiment = models.ForeignKey(Experiment, on_delete=models.CASCADE)
    setup = models.ForeignKey('Setup', on_delete=models.CASCADE)
    name = models.CharField(max_length=255, null=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES)
    started_at = models.DateTimeField(null=True)
    finished_at = models.DateTimeField(null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    notes = models.TextField(null=True)

    class Meta:
        indexes = [
            models.Index(fields=['experiment']),
            models.Index(fields=['setup']),
        ]

# 4. SETUPS:
# -----------------------------------------------------------------------------
# Defines reusable execution environments or configurations.
#
# Schema:
#   id (PK)
#   name (NOT NULL)
#   description
#   created_at (NOT NULL)

class Setup(models.Model):
    id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=255, null=False)
    description = models.TextField(null=True)
    created_at = models.DateTimeField(auto_now_add=True)

# 5. PLATFORMS:
# -----------------------------------------------------------------------------
# Represents hardware/software platforms (GPU, cloud, edge, etc.).
#
# Schema:
#   id (PK)
#   name (NOT NULL, UNIQUE)
#   description
#   created_at (NOT NULL)

class Platform(models.Model):
    id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=255, null=False, unique=True)
    description = models.TextField(null=True)
    created_at = models.DateTimeField(auto_now_add=True)

# -----------------------------------------------------------------------------
# JUNCTION TABLES
# -----------------------------------------------------------------------------


# 6. SETUP_PLATFORMS:
# -----------------------------------------------------------------------------
# Many-to-many relationship between setups and platforms.
#
# Schema:
#   setup_id (FK → setups.id)
#   platform_id (FK → platforms.id)
#   role
#   config (JSON)
#
# Primary Key:
#   (setup_id, platform_id)

class SetupPlatform(models.Model):
    setup = models.ForeignKey(Setup, on_delete=models.CASCADE)
    platform = models.ForeignKey(Platform, on_delete=models.CASCADE)
    role = models.CharField(max_length=100, null=True)
    config = models.JSONField(null=True)

    class Meta:
        unique_together = (('setup', 'platform'),)


# 6b. EXPERIMENT_SETUPS:
# -----------------------------------------------------------------------------
# Many-to-many relationship between experiments and setups.
# An experiment MUST have at least one setup.
#
# Schema:
#   experiment_id (FK -> experiments.id)
#   setup_id (FK -> setups.id)
#   notes
#
# Primary Key:
#   (experiment_id, setup_id)

class ExperimentSetup(models.Model):
    experiment = models.ForeignKey(Experiment, on_delete=models.CASCADE, related_name='experiment_setups')
    setup = models.ForeignKey(Setup, on_delete=models.CASCADE, related_name='experiment_setups')
    notes = models.TextField(null=True, blank=True)

    class Meta:
        unique_together = (('experiment', 'setup'),)

# 7. EXPERIMENT_MATERIALS:
# -----------------------------------------------------------------------------
# Links experiments with materials (datasets, configs, etc.).
#
# Schema:
#   experiment_id (FK → experiments.id)
#   material_id (FK → materials.id)
#   role
#   notes
#
# Primary Key:
#   (experiment_id, material_id)

class ExperimentMaterial(models.Model):
    experiment = models.ForeignKey(Experiment, on_delete=models.CASCADE)
    material = models.ForeignKey('Material', on_delete=models.CASCADE)
    role = models.CharField(max_length=100, null=True)
    notes = models.TextField(null=True)

    class Meta:
        unique_together = (('experiment', 'material'),)

# 8. MODEL_MATERIALS:
# -----------------------------------------------------------------------------
# Associates models with materials and defines relationship type.
#
# Schema:
#   model_id (FK → models.id)
#   material_id (FK → materials.id)
#   relation_type
#
# Primary Key:
#   (model_id, material_id)

class ModelMaterial(models.Model):
    model = models.ForeignKey(Model, on_delete=models.CASCADE)
    material = models.ForeignKey('Material', on_delete=models.CASCADE)
    relation_type = models.CharField(max_length=100, null=True)

    class Meta:
        unique_together = (('model', 'material'),)

# -----------------------------------------------------------------------------
# SUPPORTING ENTITIES
# -----------------------------------------------------------------------------


# 9. MATERIAL_TYPES:
# -----------------------------------------------------------------------------
# Defines categories of materials (dataset, script, config, etc.).
#
# Schema:
#   id (PK)
#   name (NOT NULL, UNIQUE)
#   description

class MaterialType(models.Model):
    id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=100, null=False, unique=True)
    description = models.TextField(null=True)

# 10. MATERIALS:
# -----------------------------------------------------------------------------
# Versioned assets used in experiments and models.
#
# Schema:
#   id (PK)
#   material_type_id (FK → material_types.id, NOT NULL)
#   name (NOT NULL)
#   description
#   link
#   version (NOT NULL)
#   created_at (NOT NULL)
#
# Constraints:
#   UNIQUE (name, version)

class Material(models.Model):
    id = models.AutoField(primary_key=True)
    material_type = models.ForeignKey(MaterialType, on_delete=models.CASCADE)
    name = models.CharField(max_length=255, null=False)
    description = models.TextField(null=True)
    link = models.URLField(null=True)
    version = models.CharField(max_length=50, null=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = (('name', 'version'),)

# -----------------------------------------------------------------------------
# FLEXIBLE / DYNAMIC DATA
# -----------------------------------------------------------------------------


# 11. PARAMETERS:
# -----------------------------------------------------------------------------
# Polymorphic key-value store for attaching metadata to entities.
#
# Supported entity types:
#   model, experiment, run, setup, material
#
# Schema:
#   id (PK)
#   entity_type (NOT NULL)
#   entity_id (NOT NULL)
#   key (NOT NULL)
#   value
#   value_type
#   created_at (NOT NULL)
#
# Constraints:
#   CHECK entity_type IN ('model','experiment','run','setup','material')
#
# Indexes:
#   INDEX (entity_type, entity_id)

class Parameter(models.Model):
    ENTITY_TYPE_CHOICES = [
        ('model', 'Model'),
        ('experiment', 'Experiment'),
        ('run', 'Run'),
        ('setup', 'Setup'),
        ('material', 'Material'),
    ]

    id = models.AutoField(primary_key=True)
    entity_type = models.CharField(max_length=20, choices=ENTITY_TYPE_CHOICES)
    entity_id = models.IntegerField()
    key = models.CharField(max_length=255, null=False)
    value = models.TextField(null=True)
    value_type = models.CharField(max_length=50, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=['entity_type', 'entity_id']),
        ]

# -----------------------------------------------------------------------------
# RUN DATA
# -----------------------------------------------------------------------------


# 12. RUN_METRICS:
# -----------------------------------------------------------------------------
# Stores scalar metrics for each run.
#
# Schema:
#   run_id (FK → runs.id)
#   metric_name
#   metric_value
#
# Primary Key:
#   (run_id, metric_name)

class RunMetric(models.Model):
    run = models.ForeignKey('Run', on_delete=models.CASCADE)
    metric_name = models.CharField(max_length=255, null=False)
    metric_value = models.FloatField(null=False)

    class Meta:
        unique_together = (('run', 'metric_name'),)

# 13. RUN_OUTPUTS:
# -----------------------------------------------------------------------------
# Stores artifacts, files, and results from runs.
#
# Schema:
#   id (PK)
#   run_id (FK → runs.id, NOT NULL)
#   type (NOT NULL)   # file | artifact | result
#   name
#   value
#   file
#   created_at (NOT NULL)
#
# Indexes:
#   INDEX (run_id)

class RunOutput(models.Model):

    OUTPUT_TYPES = [
        ('file', 'File'),
        ('artifact', 'Artifact'),
        ('result', 'Result'),
    ]

    id = models.AutoField(primary_key=True)
    run = models.ForeignKey('Run', on_delete=models.CASCADE, related_name='outputs')
    type = models.CharField(max_length=20, choices=OUTPUT_TYPES)
    name = models.CharField(max_length=255, null=True, blank=True)
    # For structured / text outputs (metrics, JSON, logs, etc.)
    value = models.TextField(null=True, blank=True)
    # For uploaded files (h5, pkl, csv, images, docs, etc.)
    file = models.FileField(upload_to='run_outputs/', null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=['run']),
            models.Index(fields=['type']),
        ]

# 14. RUN_LOGS:
# -----------------------------------------------------------------------------
# Stores logs generated during execution.
#
# Schema:
#   id (PK)
#   run_id (FK → runs.id, NOT NULL)
#   level (NOT NULL)   # info | warning | error
#   message (NOT NULL)
#   logged_at (NOT NULL)
#
# Indexes:
#   INDEX (run_id, logged_at)

class RunLog(models.Model):

    LOG_LEVELS = [
        ('info', 'Info'),
        ('warning', 'Warning'),
        ('error', 'Error'),
    ]

    id = models.AutoField(primary_key=True)
    run = models.ForeignKey('Run', on_delete=models.CASCADE, related_name='logs')
    level = models.CharField(max_length=20, choices=LOG_LEVELS)
    message = models.TextField(null=False)
    logged_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=['run', 'logged_at']),
        ]

# -----------------------------------------------------------------------------
# TAGGING SYSTEM
# -----------------------------------------------------------------------------


# 15. TAGS:
# -----------------------------------------------------------------------------
# Reusable labels for categorizing entities.
#
# Schema:
#   id (PK)
#   name (NOT NULL, UNIQUE)
#   color
#   created_at (NOT NULL)

class Tag(models.Model):
    id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=100, null=False, unique=True)
    color = models.CharField(max_length=7, null=True)  # Hex color code (e.g., #RRGGBB)
    created_at = models.DateTimeField(auto_now_add=True)

# 16. ENTITY_TAGS:
# -----------------------------------------------------------------------------
# Many-to-many tagging across multiple entity types.
#
# Supported entity types:
#   model, experiment, run, material, setup
#
# Schema:
#   entity_type (NOT NULL)
#   entity_id (NOT NULL)
#   tag_id (FK → tags.id)
#
# Primary Key:
#   (entity_type, entity_id, tag_id)
#
# Constraints:
#   CHECK entity_type IN ('model','experiment','run','material','setup')
#
# Indexes:
#   INDEX (entity_type, entity_id)

class EntityTag(models.Model):
    ENTITY_TYPE_CHOICES = [
        ('model', 'Model'),
        ('experiment', 'Experiment'),
        ('run', 'Run'),
        ('material', 'Material'),
        ('setup', 'Setup'),
    ]

    entity_type = models.CharField(max_length=20, choices=ENTITY_TYPE_CHOICES)
    entity_id = models.IntegerField()
    tag = models.ForeignKey(Tag, on_delete=models.CASCADE)

    class Meta:
        unique_together = (('entity_type', 'entity_id', 'tag'),)
        indexes = [
            models.Index(fields=['entity_type', 'entity_id']),
        ]
