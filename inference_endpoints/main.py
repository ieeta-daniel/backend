from fastapi import FastAPI, File, UploadFile
import docker

app = FastAPI()


@app.post("/uploadfile/")
async def create_upload_file(file: UploadFile = File(...)):
    # Process the file or extract relevant information from the request
    # ...

    # Deploy a container
    deploy_container(file)

    return {"filename": file.filename}


def deploy_container(file):
    print(file)
