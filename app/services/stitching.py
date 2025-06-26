# app/services/stitching.py
import cv2
import numpy as np
from app.config import STATIC_DIR
from datetime import datetime
from pathlib import Path
import uuid
import logging

logger = logging.getLogger(__name__)

def validate_images(images):
    """Validate that all images are loaded correctly"""
    for i, img in enumerate(images):
        if img is None:
            raise Exception(f"Impossible de charger l'image {i+1}")
        if img.size == 0:
            raise Exception(f"L'image {i+1} est vide")
    return True

def preprocess_images(images):
    """Preprocess images for better stitching"""
    processed = []
    for img in images:
        # Resize if images are too large (for performance)
        height, width = img.shape[:2]
        if width > 2000:
            scale = 2000 / width
            new_width = int(width * scale)
            new_height = int(height * scale)
            img = cv2.resize(img, (new_width, new_height))
        processed.append(img)
    return processed

def create_equirectangular_projection(panorama):
    """Convert panorama to proper equirectangular projection"""
    height, width = panorama.shape[:2]
    
    # Create mapping for equirectangular projection
    map_x = np.zeros((2048, 4096), dtype=np.float32)
    map_y = np.zeros((2048, 4096), dtype=np.float32)
    
    for y in range(2048):
        for x in range(4096):
            # Convert to spherical coordinates
            theta = (x / 4096.0) * 2 * np.pi - np.pi  # longitude
            phi = (y / 2048.0) * np.pi - np.pi/2      # latitude
            
            # Convert to panorama coordinates
            px = (theta + np.pi) / (2 * np.pi) * width
            py = (phi + np.pi/2) / np.pi * height
            
            map_x[y, x] = px
            map_y[y, x] = py
    
    # Apply mapping
    equirectangular = cv2.remap(panorama, map_x, map_y, cv2.INTER_LINEAR)
    return equirectangular

def stitch_images(image_paths):
    """Enhanced image stitching with better error handling and processing"""
    try:
        # Load images
        images = [cv2.imread(str(p)) for p in image_paths]
        validate_images(images)
        
        logger.info(f"Loaded {len(images)} images for stitching")
        
        # Preprocess images
        images = preprocess_images(images)
        
        # Try different stitching modes
        stitcher_modes = [cv2.Stitcher_PANORAMA, cv2.Stitcher_SCANS]
        panorama = None
        
        for mode in stitcher_modes:
            try:
                stitcher = cv2.Stitcher.create(mode)
                # Configure stitcher parameters
                stitcher.setPanoConfidenceThresh(0.3)
                
                status, result = stitcher.stitch(images)
                
                if status == cv2.Stitcher_OK:
                    panorama = result
                    logger.info(f"Stitching successful with mode {mode}")
                    break
                else:
                    logger.warning(f"Stitching failed with mode {mode}, status: {status}")
                    
            except Exception as e:
                logger.warning(f"Error with stitching mode {mode}: {str(e)}")
                continue
        
        if panorama is None:
            raise Exception("Échec de l'assemblage avec tous les modes disponibles")
        
        # Create proper equirectangular projection
        try:
            equirectangular = create_equirectangular_projection(panorama)
        except Exception as e:
            logger.warning(f"Equirectangular projection failed: {str(e)}, using simple resize")
            equirectangular = cv2.resize(panorama, (4096, 2048))
        
        # Generate filename
        filename = f"panorama_{uuid.uuid4().hex}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jpg"
        output_path = STATIC_DIR / filename
        
        # Save with high quality
        success = cv2.imwrite(
            str(output_path), 
            equirectangular, 
            [cv2.IMWRITE_JPEG_QUALITY, 95, cv2.IMWRITE_JPEG_PROGRESSIVE, 1]
        )
        
        if not success:
            raise Exception("Échec de la sauvegarde de l'image")
        
        logger.info(f"Panorama saved: {output_path}")
        return output_path
        
    except Exception as e:
        logger.error(f"Stitching error: {str(e)}")
        raise Exception(f"Erreur lors de l'assemblage: {str(e)}")