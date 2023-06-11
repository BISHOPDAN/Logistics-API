import os
import uuid
from pathlib import Path


def driver_upload_path(instance, folder_name):
    """
    Function to get the base path of a driver image
    in the format
    """

    logistic = instance.logistic.slug_name

    # Get driver folder name like driver_<user_profle_name>
    driver_folder_name = "driver_" + instance.user.profile.get_user_name_with_id()  # noqa

    return os.path.join(
        "logistics",
        logistic,
        "drivers",
        driver_folder_name,
        folder_name)


def driver_licence_path(instance, filename):
    """
    Get driver folder path with folder name licence
    """
    base_path = driver_upload_path(instance, 'licence')
    return Path(base_path) / filename


def driver_id_path(instance, filename):
    """
    Get driver folder path with folder name id-card
    """
    base_path = driver_upload_path(instance, 'id-card')
    return Path(base_path) / filename


def logistics_unique_filename(instance, filename):
    # Generate a unique filename using UUID
    filename = f"{instance.id}/{uuid.uuid4().hex}-{filename}"
    return os.path.join("logistics", filename)
