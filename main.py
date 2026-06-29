report = RevenueExtractor(pdf)

report.validate()

report.write_to_google_sheet()

report.save_log()