# ============================================
# SATELLITE ORBITAL RISK PREDICTION
# ============================================

args <- commandArgs(trailingOnly = TRUE)

if (length(args) < 2) {
  stop("Input CSV and model file are required")
}

input_file <- args[1]
model_file <- args[2]

# --------------------------------------------
# Load model
# --------------------------------------------

model <- readRDS(model_file)

# --------------------------------------------
# Read input
# --------------------------------------------

data <- read.csv(
  input_file,
  stringsAsFactors = FALSE,
  check.names = FALSE
)

# --------------------------------------------
# Clean satellite name
# --------------------------------------------

data$Satellite <- toupper(trimws(as.character(data$Satellite)))

# --------------------------------------------
# Allowed satellites
# --------------------------------------------

allowed_satellites <- c(
  "AQUA",
  "ICESAT2",
  "LANDSAT8",
  "SENTINEL2A",
  "SWARMA",
  "TERRA"
)

if (!(data$Satellite[1] %in% allowed_satellites)) {
  stop(
    paste(
      "Invalid satellite name:",
      data$Satellite[1]
    )
  )
}

# --------------------------------------------
# Satellite factor
# IMPORTANT:
# use the levels stored in the trained model
# --------------------------------------------

if ("Satellite" %in% names(model$xlevels)) {

  data$Satellite <- factor(
    data$Satellite,
    levels = model$xlevels$Satellite
  )

} else {

  satellite_levels <- c(
    "AQUA",
    "ICESAT2",
    "LANDSAT8",
    "SENTINEL2A",
    "SWARMA",
    "TERRA"
  )

  data$Satellite <- factor(
    data$Satellite,
    levels = satellite_levels
  )
}

# --------------------------------------------
# Required columns
# --------------------------------------------

prediction_data <- data[, c(
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
)]

# --------------------------------------------
# Prediction
# --------------------------------------------

prediction <- predict(
  model,
  prediction_data,
  type = "class"
)

probability <- predict(
  model,
  prediction_data,
  type = "prob"
)

# --------------------------------------------
# Extract probabilities
# --------------------------------------------

low_probability <- probability[1, "Low"]
medium_probability <- probability[1, "Medium"]
high_probability <- probability[1, "High"]

# --------------------------------------------
# OUTPUT FOR FASTAPI
# --------------------------------------------

cat(
  paste0(
    "Satellite=",
    as.character(data$Satellite[1]),
    "\n"
  )
)

cat(
  paste0(
    "Risk=",
    as.character(prediction[1]),
    "\n"
  )
)

cat(
  paste0(
    "Low=",
    low_probability,
    "\n"
  )
)

cat(
  paste0(
    "Medium=",
    medium_probability,
    "\n"
  )
)

cat(
  paste0(
    "High=",
    high_probability,
    "\n"
  )
)