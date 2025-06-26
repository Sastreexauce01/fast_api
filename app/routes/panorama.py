from fastapi import APIRouter, UploadFile, File, HTTPException, BackgroundTasks
from fastapi.responses import JSONResponse
from typing import List
import logging
from app.utils.files import save_uploaded_images, cleanup_files, validate_uploaded_files
from app.services.stitching import stitch_images

logger = logging.getLogger(__name__)
router = APIRouter()

@router.post("/stitch-panorama")
async def stitch_panorama(
    background_tasks: BackgroundTasks,
    files: List[UploadFile] = File(...)
):
    """
    Assembler 8 images en panorama 360° équirectangulaire
    """
    try:
        # Validation du nombre d'images
        if len(files) != 8:
            raise HTTPException(
                status_code=400, 
                detail=f"Exactement 8 images requises, {len(files)} reçues"
            )
        
        # Validation des fichiers
        validation_errors = validate_uploaded_files(files)
        if validation_errors:
            raise HTTPException(status_code=400, detail=validation_errors)
        
        # Sauvegarde des images
        saved_paths = await save_uploaded_images(files)
        
        # Nettoyage en arrière-plan
        background_tasks.add_task(cleanup_files, saved_paths)
        
        try:
            # Assemblage
            panorama_path = stitch_images(saved_paths)
            
            # Métadonnées du résultat
            file_size = panorama_path.stat().st_size
            
            return JSONResponse({
                "success": True,
                "data": {
                    "url": f"/static/{panorama_path.name}",
                    "filename": panorama_path.name,
                    "dimensions": {"width": 4096, "height": 2048},
                    "format": "equirectangular",
                    "file_size": file_size,
                    "projection": "360_panorama"
                },
                "message": "Panorama généré avec succès"
            })
            
        except Exception as e:
            logger.error(f"Stitching failed: {str(e)}")
            raise HTTPException(status_code=500, detail=str(e))
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        raise HTTPException(status_code=500, detail="Erreur interne du serveur")

@router.get("/health")
async def health_check():
    """Point de santé de l'API"""
    return {"status": "healthy", "service": "panorama-api"}