import json
import os
from pathlib import Path

from typing import Annotated

from fastapi import APIRouter, Body

import transformerlab.db as db
from transformerlab.shared import shared
from transformerlab.shared import dirs
from transformerlab.routers.experiment import rag, documents, plugins, conversations, export, evals


router = APIRouter(prefix="/experiment", tags=["experiment"])

router.include_router(
    router=rag.router, prefix="/{experimentId}", tags=["rag"])
router.include_router(
    router=documents.router, prefix="/{experimentId}", tags=["documents"])
router.include_router(
    router=plugins.router, prefix="/{id}", tags=["plugins"])
router.include_router(
    router=conversations.router, prefix="/{experimentId}", tags=["conversations"])
router.include_router(
    router=export.router, prefix="/{id}", tags=["export"])
router.include_router(
    router=evals.router, prefix="/{experimentId}", tags=["evals"])


EXPERIMENTS_DIR: str = dirs.EXPERIMENTS_DIR


@router.get("/")
async def experiments_get_all():
    return await db.experiment_get_all()


@router.get("/create")
async def experiments_create(name: str):
    newid = await db.experiment_create(name, "{}")
    return newid


@router.get("/{id}")
async def experiment_get(id: int):
    data = await db.experiment_get(id)

    # convert the JSON string called config to json object
    data["config"] = json.loads(data["config"])
    return data


@router.get("/{id}/delete")
async def experiments_delete(id: int):
    await db.experiment_delete(id)
    return {"message": f"Experiment {id} deleted"}


@router.get("/{id}/update")
async def experiments_update(id: int, name: str):
    await db.experiment_update(id, name)
    return {"message": f"Experiment {id} updated to {name}"}


@router.get("/{id}/update_config")
async def experiments_update_config(id: int, key: str, value: str):
    await db.experiment_update_config(id, key, value)
    return {"message": f"Experiment {id} updated"}


@router.post("/{id}/prompt")
async def experiments_save_prompt_template(id: int, template: Annotated[str, Body()]):
    await db.experiment_save_prompt_template(id, template)
    return {"message": f"Experiment {id} prompt template saved"}


@router.post("/{id}/save_file_contents")
async def experiment_save_file_contents(id: int, filename: str, file_contents: Annotated[str, Body()]):
    # first get the experiment name:
    data = await db.experiment_get(id)

    # if the experiment does not exist, return an error:
    if data is None:
        return {"message": f"Experiment {id} does not exist"}

    experiment_name = data["name"]

    # remove file extension from file:
    [filename, file_ext] = os.path.splitext(filename)

    if (file_ext != '.py') and (file_ext != '.ipynb') and (file_ext != '.md'):
        return {"message": f"File extension {file_ext} not supported"}

    # clean the file name:
    filename = shared.slugify(filename)

    # make directory if it does not exist:
    if not os.path.exists(f"{EXPERIMENTS_DIR}/{experiment_name}"):
        os.makedirs(f"{EXPERIMENTS_DIR}/{experiment_name}")

    # now save the file contents, overwriting if it already exists:
    with open(f"{EXPERIMENTS_DIR}/{experiment_name}/{filename}{file_ext}", "w") as f:
        f.write(file_contents)

    return {"message": f"{EXPERIMENTS_DIR}/{experiment_name}/{filename}{file_ext} file contents saved"}


@router.get("/{id}/file_contents")
async def experiment_get_file_contents(id: int, filename: str):
    # first get the experiment name:
    data = await db.experiment_get(id)

    # if the experiment does not exist, return an error:
    if data is None:
        return {"message": f"Experiment {id} does not exist"}

    experiment_name = data["name"]

    # remove file extension from file:
    [filename, file_ext] = os.path.splitext(filename)

    allowed_extensions = ['.py', '.ipynb', '.md', '.txt']

    if file_ext not in allowed_extensions:
        return {"message": f"File extension {file_ext} for {filename} not supported"}

    # clean the file name:
    # filename = shared.slugify(filename)

    # The following prevents path traversal attacks:
    experiment_dir = dirs.experiment_dir_by_name(experiment_name)
    final_path = Path(experiment_dir).joinpath(
        filename + file_ext).resolve().relative_to(experiment_dir)

    final_path = experiment_dir + "/" + str(final_path)
    print("Listing Contents of File: " + final_path)

    # now get the file contents
    try:
        with open(final_path, "r") as f:
            file_contents = f.read()
    except FileNotFoundError:
        return ""

    return file_contents