from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import subprocess
import tempfile
import os
import csv


# ============================================
# FASTAPI APPLICATION
# ============================================

app = FastAPI(
    title="Satellite Orbital Risk API",
    description="Satellite orbital decay risk prediction",
    version="1.0"
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================
# INPUT MODEL
# ============================================

class SatelliteData(BaseModel):

    Satellite: str
    MEAN_MOTION: float
    ECCENTRICITY: float
    INCLINATION: float
    BSTAR: float
    Ap: float
    SN: float
    F107obs: float
    F107adj: float
    SEMIMAJOR_AXIS: float


# ============================================
# PATHS
# ============================================

BASE_DIR = os.path.dirname(
    os.path.abspath(__file__)
)

R_SCRIPT = os.path.join(
    BASE_DIR,
    "predict_risk.R"
)

MODEL_FILE = os.path.join(
    BASE_DIR,
    "orbital_risk_model.rds"
)

# IMPORTANT:
# Change this only if your R installation
# is in another location.

RSCRIPT_EXE = r"C:\Program Files\R\R-4.6.1\bin\Rscript.exe"


# ============================================
# HOME
# ============================================

@app.get("/")
def home():

    return {
        "message": "Satellite Orbital Risk API is running",
        "status": "success"
    }


# ============================================
# PREDICTION
# ============================================

@app.post("/predict")
def predict_risk(data: SatelliteData):

    # ----------------------------------------
    # Clean satellite name
    # ----------------------------------------

    satellite = data.Satellite.strip().upper()

    allowed_satellites = [
        "AQUA",
        "ICESAT2",
        "LANDSAT8",
        "SENTINEL2A",
        "SWARMA",
        "TERRA"
    ]

    if satellite not in allowed_satellites:

        raise HTTPException(
            status_code=400,
            detail=f"Invalid satellite name: {satellite}"
        )

    # ----------------------------------------
    # Check files
    # ----------------------------------------

    if not os.path.exists(RSCRIPT_EXE):

        raise HTTPException(
            status_code=500,
            detail=f"Rscript not found: {RSCRIPT_EXE}"
        )

    if not os.path.exists(R_SCRIPT):

        raise HTTPException(
            status_code=500,
            detail=f"predict_risk.R not found: {R_SCRIPT}"
        )

    if not os.path.exists(MODEL_FILE):

        raise HTTPException(
            status_code=500,
            detail=f"Model not found: {MODEL_FILE}"
        )

    # ----------------------------------------
    # Temporary CSV
    # ----------------------------------------

    temp_file = tempfile.NamedTemporaryFile(
        mode="w",
        suffix=".csv",
        delete=False,
        newline="",
        encoding="utf-8"
    )

    temp_path = temp_file.name

    try:

        writer = csv.writer(temp_file)

        writer.writerow([
            "Satellite",
            "MEAN_MOTION",
            "ECCENTRICITY",
            "INCLINATION",
            "BSTAR",
            "Ap",
            "SN",
            "F107obs",
            "F107adj",
            "SEMIMAJOR_AXIS"
        ])

        writer.writerow([
            satellite,
            data.MEAN_MOTION,
            data.ECCENTRICITY,
            data.INCLINATION,
            data.BSTAR,
            data.Ap,
            data.SN,
            data.F107obs,
            data.F107adj,
            data.SEMIMAJOR_AXIS
        ])

        temp_file.close()

        # ------------------------------------
        # Run R
        # ------------------------------------

        result = subprocess.run(
            [
                RSCRIPT_EXE,
                R_SCRIPT,
                temp_path,
                MODEL_FILE
            ],
            capture_output=True,
            text=True
        )

        # ------------------------------------
        # R failed
        # ------------------------------------

        if result.returncode != 0:

            raise HTTPException(
                status_code=500,
                detail={
                    "message": "R prediction failed",
                    "error": result.stderr,
                    "output": result.stdout
                }
            )

        # ------------------------------------
        # Parse R output
        # ------------------------------------

        output = result.stdout.strip()

        predicted_satellite = None
        risk = None

        low = 0.0
        medium = 0.0
        high = 0.0

        for line in output.splitlines():

            line = line.strip()

            if line.startswith("Satellite="):

                predicted_satellite = (
                    line.split("=", 1)[1].strip()
                )

            elif line.startswith("Risk="):

                risk = (
                    line.split("=", 1)[1].strip()
                )

            elif line.startswith("Low="):

                low = float(
                    line.split("=", 1)[1].strip()
                )

            elif line.startswith("Medium="):

                medium = float(
                    line.split("=", 1)[1].strip()
                )

            elif line.startswith("High="):

                high = float(
                    line.split("=", 1)[1].strip()
                )

        # ------------------------------------
        # Check result
        # ------------------------------------

        if risk is None:

            raise HTTPException(
                status_code=500,
                detail={
                    "message": "Could not read prediction from R",
                    "output": output
                }
            )

        # ------------------------------------
        # Return JSON
        # ------------------------------------

        return {

            "status": "success",

            "satellite": predicted_satellite,

            "predicted_risk": risk,

            "probabilities": {

                "Low": round(low * 100, 2),

                "Medium": round(medium * 100, 2),

                "High": round(high * 100, 2)

            }

        }

    finally:

        # ------------------------------------
        # Delete temporary CSV
        # ------------------------------------

        if os.path.exists(temp_path):

            os.remove(temp_path)