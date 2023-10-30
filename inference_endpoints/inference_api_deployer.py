import docker
from kubernetes import client, config
import tempfile
import shutil
import os

from kubernetes.client import V1Deployment, V1ObjectMeta, V2HorizontalPodAutoscalerSpec, V2CrossVersionObjectReference


def build_docker_image(image_name, handler_path, requirements_path, dockerfile_path):
    # Create a temporary directory to stage the code
    staging_dir = tempfile.mkdtemp()
    try:
        # Copy the handler.py and any other dependencies to the staging directory
        staged_handler_path = os.path.join(staging_dir, 'handler.py')
        staged_requirements_path = os.path.join(staging_dir, 'requirements.txt')
        staged_dockerfile_path = os.path.join(staging_dir, 'Dockerfile')

        shutil.copy(handler_path, staged_handler_path)
        shutil.copy(requirements_path, staged_requirements_path)
        shutil.copy(dockerfile_path, staged_dockerfile_path)

        # Build the Docker image with the code
        docker_client = docker.from_env()
        docker_client.images.build(
            dockerfile=staged_dockerfile_path,
            path=staging_dir,
            tag=image_name,
        )
    finally:
        # Clean up the temporary directory
        shutil.rmtree(staging_dir)


def create_namespace(namespace):
    # Load the Kubernetes configuration (e.g., from ~/.kube/config or an in-cluster configuration)
    config.load_kube_config()

    # Define the Kubernetes API client
    core_api_instance = client.CoreV1Api()

    # Define the namespace
    namespace = client.V1Namespace(metadata=client.V1ObjectMeta(name=namespace))

    # Create the namespace
    core_api_instance.create_namespace(namespace)


def create_kubernetes_deployment(namespace, model_name, image_name, min_replicas, max_replicas, container_port=5000):
    # Load the Kubernetes configuration (e.g., from ~/.kube/config or an in-cluster configuration)
    config.load_kube_config()

    # Define the Kubernetes API client
    api_instance = client.AppsV1Api()

    # Define the Deployment metadata
    metadata = client.V1ObjectMeta(name=model_name)

    # Define the container spec
    container = client.V1Container(
        # we don't want to pull the image from a registry (since we built it locally).
        # This is not recommended for production.
        image_pull_policy="IfNotPresent",
        restart_policy="OnFailure",
        name=model_name,
        image=image_name,
        resources=client.V1ResourceRequirements(
            limits={"cpu": "2", "memory": "1Gi"},
        ),
        ports=[
            client.V1ContainerPort(container_port=container_port)
        ]
    )

    # Define the Pod spec
    pod_spec = client.V1PodSpec(
        containers=[container],
    )

    # Define the Pod template
    pod_template = client.V1PodTemplateSpec(
        metadata=client.V1ObjectMeta(labels={"app": model_name}),
        spec=pod_spec,
    )

    # Define the Deployment spec
    deployment_spec = client.V1DeploymentSpec(
        replicas=min_replicas,
        selector=client.V1LabelSelector(match_labels={"app": model_name}),
        template=pod_template,
    )

    # Create the Deployment
    deployment = V1Deployment(
        api_version="apps/v1",
        kind="Deployment",
        metadata=metadata,
        spec=deployment_spec,
    )

    # Create the Deployment in the specified namespace
    api_instance.create_namespaced_deployment(namespace, deployment)

    # Create Horizontal Pod Autoscaler (HPA)
    hpa_metadata = V1ObjectMeta(name=model_name)
    hpa_reference = V2CrossVersionObjectReference(kind="Deployment", name=model_name)
    hpa_spec = V2HorizontalPodAutoscalerSpec(
        scale_target_ref=hpa_reference,
        min_replicas=min_replicas,
        max_replicas=max_replicas,
        metrics=[],
    )
    body = client.V2HorizontalPodAutoscaler(
        api_version="autoscaling/v2",
        kind='HorizontalPodAutoscaler',
        metadata=hpa_metadata,
        spec=hpa_spec,
    )

    hpa_api_instance = client.AutoscalingV2Api()

    hpa_api_instance.create_namespaced_horizontal_pod_autoscaler(namespace, body, pretty=True)


def create_kubernetes_service(namespace, service_name, deployment_name, target_port, node_port=None):
    # Load the Kubernetes configuration
    config.load_kube_config()

    # Define the Kubernetes API client
    core_api_instance = client.CoreV1Api()

    # Define the Service metadata
    service_metadata = client.V1ObjectMeta(name=service_name)

    # Define the Service spec
    service_spec = client.V1ServiceSpec(
        selector={"app": deployment_name},  # Match labels to select Pods
        ports=[client.V1ServicePort(
            port=80,  # Port on which the Service listens
            target_port=target_port,  # Port on which your Pods are listening
        )]
    )

    # If you want to create a NodePort Service, specify the node_port
    if node_port is not None:
        service_spec.type = "NodePort"
        service_spec.ports[0].node_port = node_port

    # Create the Service in the specified namespace
    service = client.V1Service(
        api_version="v1",
        kind="Service",
        metadata=service_metadata,
        spec=service_spec
    )

    core_api_instance.create_namespaced_service(namespace, service)


def main():
    # Define the model-specific information
    namespace = "danie"
    model_name = "model-name"
    service_name = "service-name"
    handler_path = "handler.py"
    requirements_path = "requirements.txt"
    dockerfile_path = "Dockerfile"
    image_name = "local-image:latest"  # Image name without a registry
    min_replicas = 1
    max_replicas = 3

    build_docker_image(image_name, handler_path, requirements_path, dockerfile_path)
    create_namespace(namespace)
    create_kubernetes_deployment(namespace, model_name, image_name, min_replicas, max_replicas)
    create_kubernetes_service(namespace, service_name, model_name, 5000)


if __name__ == "__main__":
    main()
