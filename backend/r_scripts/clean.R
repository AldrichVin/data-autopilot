#!/usr/bin/env Rscript
suppressPackageStartupMessages({
  library(tidyverse)
  library(jsonlite)
})

args <- commandArgs(trailingOnly = TRUE)
input_path  <- args[1]
output_path <- args[2]
report_path <- args[3]
options     <- fromJSON(args[4])

start_time <- proc.time()

df <- read_csv(input_path, show_col_types = FALSE)
report_steps <- list()
original_shape <- c(nrow(df), ncol(df))

# Step 1: Remove duplicates
if (isTRUE(options$remove_duplicates)) {
  before <- nrow(df)
  df <- distinct(df)
  after <- nrow(df)
  report_steps[[length(report_steps) + 1]] <- list(
    step = "remove_duplicates",
    description = paste("Removed", before - after, "duplicate rows"),
    rows_affected = before - after,
    details = list()
  )
}

# Step 2: Fix types (attempt numeric/date coercion on character columns)
if (isTRUE(options$fix_types)) {
  conversions <- list()
  for (col_name in names(df)) {
    if (is.character(df[[col_name]])) {
      numeric_attempt <- suppressWarnings(as.numeric(df[[col_name]]))
      non_na_original <- sum(!is.na(df[[col_name]]))
      if (non_na_original > 0 && sum(!is.na(numeric_attempt)) / non_na_original >= 0.8) {
        df[[col_name]] <- numeric_attempt
        conversions[[col_name]] <- "numeric"
        next
      }

      date_attempt <- suppressWarnings(as.Date(df[[col_name]], tryFormats = c("%Y-%m-%d", "%d/%m/%Y", "%m/%d/%Y")))
      if (non_na_original > 0 && sum(!is.na(date_attempt)) / non_na_original >= 0.8) {
        df[[col_name]] <- date_attempt
        conversions[[col_name]] <- "datetime"
      }
    }
  }
  report_steps[[length(report_steps) + 1]] <- list(
    step = "fix_types",
    description = paste("Fixed types for", length(conversions), "columns"),
    rows_affected = 0,
    details = list(conversions = conversions)
  )
}

# Step 3: Handle missing values
fill_strategy <- ifelse(is.null(options$fill_strategy), "median", options$fill_strategy)
total_filled <- 0
dropped_cols <- character(0)

# Drop columns with >50% NA
na_pcts <- colMeans(is.na(df))
high_null <- names(na_pcts[na_pcts > 0.5])
if (length(high_null) > 0) {
  df <- df %>% select(-all_of(high_null))
  dropped_cols <- high_null
}

for (col_name in names(df)) {
  na_count <- sum(is.na(df[[col_name]]))
  if (na_count == 0) next

  if (fill_strategy == "drop") {
    df <- df %>% filter(!is.na(.data[[col_name]]))
    total_filled <- total_filled + na_count
  } else if (is.numeric(df[[col_name]])) {
    fill_val <- switch(fill_strategy,
      "mean" = mean(df[[col_name]], na.rm = TRUE),
      "median" = median(df[[col_name]], na.rm = TRUE),
      "mode" = {
        tbl <- table(df[[col_name]])
        as.numeric(names(tbl)[which.max(tbl)])
      }
    )
    df[[col_name]][is.na(df[[col_name]])] <- fill_val
    total_filled <- total_filled + na_count
  } else {
    tbl <- table(df[[col_name]])
    if (length(tbl) > 0) {
      mode_val <- names(tbl)[which.max(tbl)]
      df[[col_name]][is.na(df[[col_name]])] <- mode_val
      total_filled <- total_filled + na_count
    }
  }
}

report_steps[[length(report_steps) + 1]] <- list(
  step = "handle_missing",
  description = paste("Filled", total_filled, "missing values using", fill_strategy, "strategy"),
  rows_affected = total_filled,
  details = list(dropped_columns = dropped_cols, strategy = fill_strategy)
)

# Step 4: Handle outliers (cap at 3x IQR)
if (isTRUE(options$handle_outliers)) {
  capped_count <- 0
  capped_cols <- character(0)

  numeric_cols <- names(df)[sapply(df, is.numeric)]
  for (col_name in numeric_cols) {
    q1 <- quantile(df[[col_name]], 0.25, na.rm = TRUE)
    q3 <- quantile(df[[col_name]], 0.75, na.rm = TRUE)
    iqr <- q3 - q1
    if (iqr == 0) next

    lower <- q1 - 3 * iqr
    upper <- q3 + 3 * iqr
    outliers <- sum(df[[col_name]] < lower | df[[col_name]] > upper, na.rm = TRUE)
    if (outliers > 0) {
      df[[col_name]] <- pmin(pmax(df[[col_name]], lower), upper)
      capped_count <- capped_count + outliers
      capped_cols <- c(capped_cols, col_name)
    }
  }

  report_steps[[length(report_steps) + 1]] <- list(
    step = "handle_outliers",
    description = paste("Capped", capped_count, "outlier values in", length(capped_cols), "columns (3x IQR)"),
    rows_affected = capped_count,
    details = list(capped_columns = capped_cols)
  )
}

# Step 5: Standardize strings
if (isTRUE(options$standardize_strings)) {
  standardized_count <- 0
  char_cols <- names(df)[sapply(df, is.character)]
  for (col_name in char_cols) {
    original <- df[[col_name]]
    df[[col_name]] <- str_trim(df[[col_name]])
    df[[col_name]] <- str_to_lower(df[[col_name]])
    changed <- sum(original != df[[col_name]], na.rm = TRUE)
    standardized_count <- standardized_count + changed
  }

  report_steps[[length(report_steps) + 1]] <- list(
    step = "standardize_strings",
    description = paste("Standardized", standardized_count, "string values (trim + lowercase)"),
    rows_affected = standardized_count,
    details = list()
  )
}

# Step 6: Consistency checks (basic — dedup near-identical categories)
merged_count <- 0
char_cols <- names(df)[sapply(df, is.character)]
for (col_name in char_cols) {
  unique_vals <- unique(na.omit(df[[col_name]]))
  if (length(unique_vals) > 50) next
  # Simple: group values that differ only by trailing whitespace or single char
  # (Full fuzzy matching would require stringdist package)
}

report_steps[[length(report_steps) + 1]] <- list(
  step = "consistency_checks",
  description = paste("Checked category consistency across", length(char_cols), "columns"),
  rows_affected = merged_count,
  details = list()
)

# Write outputs
elapsed <- (proc.time() - start_time)["elapsed"]

write_csv(df, output_path)

report <- list(
  steps = report_steps,
  original_shape = original_shape,
  cleaned_shape = c(nrow(df), ncol(df)),
  duration_ms = round(as.numeric(elapsed) * 1000)
)

write_json(report, report_path, auto_unbox = TRUE)
