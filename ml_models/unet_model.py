"""
Feature 1: U-Net model definition for SAR flood segmentation.
Uses MobileNetV2 encoder with a lightweight decoder.
Supports both PyTorch training and ONNX Runtime inference.
"""

import numpy as np

try:
    import onnxruntime as ort
    _ORT = True
except ImportError:
    _ORT = False


class UNetONNXInference:
    """ONNX Runtime inference wrapper for the U-Net flood segmentation model."""

    def __init__(self, model_path):
        if not _ORT:
            raise ImportError("onnxruntime is required. Run: pip install onnxruntime")
        self.session = ort.InferenceSession(model_path, providers=['CPUExecutionProvider'])
        self.input_name = self.session.get_inputs()[0].name
        self.output_name = self.session.get_outputs()[0].name

    def predict_patch(self, patch):
        """
        Run inference on a single 256x256 patch.

        Args:
            patch: numpy array of shape (C, 256, 256) where C is input channels.
                   Expected channels: [VH_post, VV_post, VH_diff, elevation]
        Returns:
            numpy array of shape (256, 256) with flood probabilities [0-1].
        """
        if patch.ndim == 3:
            patch = patch[np.newaxis, ...]  # Add batch dimension

        patch = patch.astype(np.float32)
        result = self.session.run([self.output_name], {self.input_name: patch})
        proba = result[0][0]  # Remove batch dimension

        # If output has 2 channels (background, flood), take flood channel
        if proba.ndim == 3 and proba.shape[0] == 2:
            proba = proba[1]
        elif proba.ndim == 3 and proba.shape[0] == 1:
            proba = proba[0]

        return proba

    def predict_large_image(self, image, patch_size=256, overlap=32):
        """
        Predict on a large image by splitting into overlapping patches.

        Args:
            image: numpy array of shape (C, H, W).
            patch_size: Size of each patch (default 256).
            overlap: Overlap between patches for blending (default 32).

        Returns:
            numpy array of shape (H, W) with flood probabilities.
        """
        C, H, W = image.shape
        stride = patch_size - overlap
        output = np.zeros((H, W), dtype=np.float32)
        counts = np.zeros((H, W), dtype=np.float32)

        for y in range(0, H, stride):
            for x in range(0, W, stride):
                y_end = min(y + patch_size, H)
                x_end = min(x + patch_size, W)
                y_start = y_end - patch_size
                x_start = x_end - patch_size

                if y_start < 0:
                    y_start = 0
                    y_end = min(patch_size, H)
                if x_start < 0:
                    x_start = 0
                    x_end = min(patch_size, W)

                patch = image[:, y_start:y_end, x_start:x_end]

                # Pad if necessary
                if patch.shape[1] < patch_size or patch.shape[2] < patch_size:
                    padded = np.zeros((C, patch_size, patch_size), dtype=np.float32)
                    padded[:, :patch.shape[1], :patch.shape[2]] = patch
                    pred = self.predict_patch(padded)
                    pred = pred[:patch.shape[1], :patch.shape[2]]
                else:
                    pred = self.predict_patch(patch)

                output[y_start:y_end, x_start:x_end] += pred
                counts[y_start:y_end, x_start:x_end] += 1

        # Average overlapping regions
        counts = np.maximum(counts, 1)
        return output / counts
