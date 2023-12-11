from fastapi import FastAPI, File, UploadFile
from kubernetes import client, config
import docker

app = FastAPI()


@app.get("/")
async def create_upload_file():
    # Process the file or extract relevant information from the request
    # ...

    # Deploy a container
    result = deploy_container()

    return result


def deploy_container():
    # Use Kubernetes client to interact with the Minikube cluster
    try:
        config.load_kube_config()
        print("Successfully loaded Kubernetes configuration")
        v1 = client.CoreV1Api()
        pod = v1.read_namespaced_pod(name="test-pod", namespace="default")

        # Print container status
        container_status = pod.status.container_statuses[0]
        print(f"Container Status: {container_status.state}")

        # You can perform additional checks or operations here

        return {"status": "success", "message": "Container accessed successfully"}
    except Exception as e:
        return {"status": "error", "message": str(e)}
