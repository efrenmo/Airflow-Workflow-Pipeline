"""
DAG to create a workflow to:
- ingest raw files from s3
- process raw files using Spark in AWS EMR and output parquet files
- load parquet files in Snowflake data warehouse
"""

from datetime import datetime, timedelta

from airflow import DAG
from airflow.operators.bash import BashOperator
from airflow.operators.python import BranchPythonOperator, PythonOperator
from airflow.providers.amazon.aws.operators.emr import (
    EmrAddStepsOperator,
    EmrCreateJobFlowOperator,
)
from airflow.providers.amazon.aws.operators.s3 import S3ListOperator
from airflow.providers.amazon.aws.sensors.emr import EmrStepSensor
from airflow.providers.snowflake.operators.snowflake import SnowflakeOperator


def _branch_func(ti=None):
    """python branch operator function to pull xcom pushed by previous list_objects_task
    to check list S3 bucket and validate if file exists, if file doesn't exist then
    return the task name notify vendor
    """
    xcom_value = ti.xcom_pull(task_ids="list_objects_task")
    print(f"received xcom_value {xcom_value}")
    if xcom_value:
        return "emr_process_file"
    else:
        return "notify_vendor"


def _notify_vendor():
    """TODO: implement the email or slack function to notify vendor about the filem misssing"""
    print("sales missing")


default_args = {
    "owner": "data_engineer",
    "depends_on_past": True,
    "start_date": datetime(2024, 1, 5),
    "end_date": datetime(2024, 1, 6),
    "email_on_failure": False,
    "email_on_retry": False,
    "snowflake_conn_id": "snowflake_default",
    "max_active_runs": 1,
    # 'retries': 1,
    # 'retry_delay': timedelta(minutes=5),
}


dag = DAG(
    "mydag",
    default_args=default_args,
    description="DAG to list objects in an S3 bucket",
    template_searchpath="/opt/airflow/dags/dependencies/",
    catchup=True,
    schedule_interval="0 6 * * *",
)

dag.doc_md = __doc__

s3_bucket = "phase-3-airflow-lab-bucket"

CLUSTER_ID = "j-2IZ0LTDTCM8QV"  # create a new EMR cluster in AWS management console or create w/ EmrCreateJobFlowOperator

# this is just an example of how to use SPARK_STEPS, you need to define your own steps
SPARK_STEPS = [
    {
        "Name": "sales_processing",
        "ActionOnFailure": "CONTINUE",
        "HadoopJarStep": {
            "Jar": "command-runner.jar",
            "Args": [
                "/usr/bin/spark-submit",
                "--master",
                "yarn",
                #    "--deploy-mode",
                #    "cluster",
                #    "--num-executors",
                #    "2",
                #    "--driver-memory",
                #    "512m",
                #    "--executor-memory",
                #    "3g",
                #    "--executor-cores",
                #    "2",
                "s3://phase-3-airflow-lab-bucket/pyspark_sales.py",
                "{{  macros.ds_format(ds,'%Y-%m-%d','%Y%m%d')  }}",
                f"s3://{s3_bucket}/"
                + "{{ macros.ds_format(ds, '%Y-%m-%d', '%Y/%m/%d') }}/",
            ],
        },
    }
]


list_objects_task = S3ListOperator(
    task_id="list_objects_task",
    bucket=s3_bucket,
    prefix="{{ macros.ds_format(ds, '%Y-%m-%d', '%Y/%m/%d') }}",
    delimiter="",  # Optional delimiter to use when listing objects
    # aws_conn_id="aws_default",
    dag=dag,
)

check_s3_file_exist = BranchPythonOperator(
    task_id="check_s3_file_exist", python_callable=_branch_func, dag=dag
)

notify_vendor = PythonOperator(
    task_id="notify_vendor", python_callable=_notify_vendor, dag=dag
)

emr_process_file = BashOperator(
    task_id="emr_process_file", bash_command="echo processing files", dag=dag
)

# Create EMR Cluster use below template to create EMR
# create_emr_cluster = EmrCreateJobFlowOperator(
#     task_id="create_emr_cluster",
#     job_flow_overrides={
#         "Name": "MyEMRCluster",
#         "ReleaseLabel": "emr-6.3.0",
#         "Applications": [{"Name": "Spark"}],
#         "Instances": {
#             'InstanceGroups': [
#             {
#                 "InstanceCount":1,
#                 "InstanceGroupType":"MASTER",
#                 "Name":"Primary",
#                 "InstanceType":"m5.xlarge",
#                 "EbsConfiguration":{
#                     "EbsBlockDeviceConfigs":[
#                         {
#                         "VolumeSpecification":{
#                             "VolumeType":"gp2",
#                             "SizeInGB":32
#                         },
#                         "VolumesPerInstance":2
#                         }
#                     ]
#                 }
#             },
#             {
#                 "InstanceCount":1,
#                 "InstanceGroupType":"CORE",
#                 "Name":"Core",
#                 "InstanceType":"m5.xlarge",
#                 "EbsConfiguration":{
#                     "EbsBlockDeviceConfigs":[
#                         {
#                         "VolumeSpecification":{
#                             "VolumeType":"gp2",
#                             "SizeInGB":32
#                         },
#                         "VolumesPerInstance":2
#                         }
#                     ]
#                 }
#             }
#             ],
#             'KeepJobFlowAliveWhenNoSteps': False,
#             'TerminationProtected': False,
#             'Ec2SubnetId': '<AWS_Subnet_ID>',
#             "Ec2KeyName": "tgam-laptop",
#         },
#     },
#     aws_conn_id="aws_default",
#     emr_conn_id="emr_conn",
#     region_name="us-east-1",
#     dag=dag,
# )

# Add and run first Spark Jar step
add_step_job = EmrAddStepsOperator(
    task_id="add_step_job",
    # job_flow_id="{{ task_instance.xcom_pull(task_ids='create_emr_cluster')['JobFlowId'] }}",
    job_flow_id=CLUSTER_ID,
    steps=SPARK_STEPS,
    dag=dag,
)

# Wait for first Spark Jar step to complete
wait_for_step_job = EmrStepSensor(
    task_id="wait_for_step_job",
    # job_flow_id="{{ task_instance.xcom_pull(task_ids='create_emr_cluster')['JobFlowId'] }}",
    job_flow_id=CLUSTER_ID,
    step_id="{{ task_instance.xcom_pull(task_ids='add_step_job')[0] }}",
    aws_conn_id="aws_default",
    dag=dag,
)

load_snowflake = SnowflakeOperator(
    task_id="load_snowflake",
    database="sales_db",
    schema="sales_schema",
    sql="sf_load.sql",
)

(list_objects_task >> check_s3_file_exist >> [notify_vendor, emr_process_file])

(
    emr_process_file
    # >> create_emr_cluster
    >> add_step_job
    >> wait_for_step_job
    >> load_snowflake
)
