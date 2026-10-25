from pathlib import Path

from PIL import Image

import cv2

import numpy as np

IMAGE_EXTENSIONS = {

    ".png",

    ".jpg",

    ".jpeg",

    ".bmp",

    ".webp",

    ".tif",

    ".tiff",

}

def is_image_file(path: Path) -> bool:

    return path.suffix.lower() in IMAGE_EXTENSIONS

def load_image(path: str):

    image = cv2.imread(str(path), cv2.IMREAD_COLOR)

    if image is None:

        raise ValueError(f"Unable to load image: {path}")

    return image

def save_image(path: str, image) -> str:

    output = Path(path)

    output.parent.mkdir(parents=True, exist_ok=True)

    success = cv2.imwrite(str(output), image)

    if not success:

        raise IOError(f"Unable to save image: {output}")

    return str(output)

def normalize_image(image):

    if image is None:

        return None

    if len(image.shape) == 2:

        return cv2.cvtColor(image, cv2.COLOR_GRAY2BGR)

    return image

def resize_for_comparison(image, max_size=512):

    image = normalize_image(image)

    height, width = image.shape[:2]

    scale = min(

        max_size / width,

        max_size / height,

        1.0,

    )

    if scale == 1.0:

        return image

    new_width = max(1, int(width * scale))

    new_height = max(1, int(height * scale))

    return cv2.resize(

        image,

        (new_width, new_height),

        interpolation=cv2.INTER_AREA,

    )

def image_hash(image):

    """

    Perceptual hash.

    Useful for exact / near-exact image detection.

    """

    image = normalize_image(image)

    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

    gray = cv2.resize(

        gray,

        (32, 32),

        interpolation=cv2.INTER_AREA,

    )

    average = gray.mean()

    bits = gray > average

    return bits.flatten()

def hash_similarity(hash_a, hash_b):

    if hash_a is None or hash_b is None:

        return 0.0

    if len(hash_a) != len(hash_b):

        return 0.0

    distance = np.count_nonzero(hash_a != hash_b)

    return 1.0 - (distance / len(hash_a))

def image_entropy(image):

    gray = cv2.cvtColor(

        normalize_image(image),

        cv2.COLOR_BGR2GRAY,

    )

    histogram = cv2.calcHist(

        [gray],

        [0],

        None,

        [256],

        [0, 256],

    )

    histogram = histogram / histogram.sum()

    entropy = -np.sum(

        histogram * np.log2(histogram + 1e-10)

    )

    return float(entropy)

def image_quality_score(image):

    gray = cv2.cvtColor(

        normalize_image(image),

        cv2.COLOR_BGR2GRAY,

    )

    variance = cv2.Laplacian(

        gray,

        cv2.CV_64F,

    ).var()

    score = min(

        max(variance / 500.0, 0.0),

        1.0,

    )

    return float(score)