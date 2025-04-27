

# Create a test snippet file
def process_data(data_list):
    """Process a list of numeric data."""
    results = []
    for item in data_list:
        if isinstance(item, (int, float)):
            results.append(item * 2)
        else:
            print(f"Skipping non-numeric item: {item}")
    return results


# Example usage
sample_data = [1, 2, "3", 4.5, "text"]
processed = process_data(sample_data)
print(f"Processed data: {processed}")
