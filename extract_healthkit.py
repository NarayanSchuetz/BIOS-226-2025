#!/usr/bin/env python3
"""
Apple HealthKit XML Export Extractor

Parses Apple Health export.xml and extracts data to CSV files.
Uses memory-efficient iterparse for large files.

Usage:
    python extract_healthkit.py data/raw_health_export.xml --output data/
"""

import argparse
import xml.etree.ElementTree as ET
from pathlib import Path
import pandas as pd
from typing import Iterator, Dict, Any, Optional


def parse_records(xml_path: str) -> Iterator[Dict[str, Any]]:
    """
    Parse Record elements from HealthKit XML using memory-efficient iterparse.

    Yields dictionaries with record attributes.
    """
    context = ET.iterparse(xml_path, events=('end',))

    for event, elem in context:
        if elem.tag == 'Record':
            yield {
                'type': elem.get('type'),
                'value': elem.get('value'),
                'unit': elem.get('unit'),
                'sourceName': elem.get('sourceName'),
                'sourceVersion': elem.get('sourceVersion'),
                'device': elem.get('device'),
                'creationDate': elem.get('creationDate'),
                'startDate': elem.get('startDate'),
                'endDate': elem.get('endDate'),
            }
            # Clear element to free memory
            elem.clear()

        # Also clear parent elements we don't need
        if elem.tag in ('HealthData', 'Correlation'):
            elem.clear()


def parse_workouts(xml_path: str) -> Iterator[Dict[str, Any]]:
    """
    Parse Workout elements from HealthKit XML.

    Yields dictionaries with workout attributes.
    """
    context = ET.iterparse(xml_path, events=('end',))

    for event, elem in context:
        if elem.tag == 'Workout':
            yield {
                'workoutActivityType': elem.get('workoutActivityType'),
                'duration': elem.get('duration'),
                'durationUnit': elem.get('durationUnit'),
                'totalDistance': elem.get('totalDistance'),
                'totalDistanceUnit': elem.get('totalDistanceUnit'),
                'totalEnergyBurned': elem.get('totalEnergyBurned'),
                'totalEnergyBurnedUnit': elem.get('totalEnergyBurnedUnit'),
                'sourceName': elem.get('sourceName'),
                'sourceVersion': elem.get('sourceVersion'),
                'device': elem.get('device'),
                'creationDate': elem.get('creationDate'),
                'startDate': elem.get('startDate'),
                'endDate': elem.get('endDate'),
            }
            elem.clear()

        if elem.tag == 'HealthData':
            elem.clear()


def parse_activity_summary(xml_path: str) -> Iterator[Dict[str, Any]]:
    """
    Parse ActivitySummary elements from HealthKit XML.

    Yields dictionaries with daily activity ring data.
    """
    context = ET.iterparse(xml_path, events=('end',))

    for event, elem in context:
        if elem.tag == 'ActivitySummary':
            yield {
                'dateComponents': elem.get('dateComponents'),
                'activeEnergyBurned': elem.get('activeEnergyBurned'),
                'activeEnergyBurnedGoal': elem.get('activeEnergyBurnedGoal'),
                'activeEnergyBurnedUnit': elem.get('activeEnergyBurnedUnit'),
                'appleMoveTime': elem.get('appleMoveTime'),
                'appleMoveTimeGoal': elem.get('appleMoveTimeGoal'),
                'appleExerciseTime': elem.get('appleExerciseTime'),
                'appleExerciseTimeGoal': elem.get('appleExerciseTimeGoal'),
                'appleStandHours': elem.get('appleStandHours'),
                'appleStandHoursGoal': elem.get('appleStandHoursGoal'),
            }
            elem.clear()

        if elem.tag == 'HealthData':
            elem.clear()


def extract_with_progress(
    parser_func,
    xml_path: str,
    output_path: str,
    name: str,
    progress_interval: int = 100000
) -> int:
    """
    Extract data using the given parser function with progress reporting.

    Args:
        parser_func: Generator function that yields record dictionaries
        xml_path: Path to XML file
        output_path: Path to output CSV
        name: Name of data type for progress messages
        progress_interval: How often to print progress

    Returns:
        Number of records extracted
    """
    records = []
    count = 0

    print(f"Extracting {name}...")

    for record in parser_func(xml_path):
        records.append(record)
        count += 1

        if count % progress_interval == 0:
            print(f"  Processed {count:,} {name}...")

    if records:
        df = pd.DataFrame(records)
        df.to_csv(output_path, index=False)
        print(f"  Saved {count:,} {name} to {output_path}")
    else:
        print(f"  No {name} found")

    return count


def extract_all(xml_path: str, output_dir: str, types: Optional[list] = None):
    """
    Extract all data types from HealthKit XML.

    Args:
        xml_path: Path to the HealthKit export XML file
        output_dir: Directory to save CSV files
        types: Optional list of types to extract ('records', 'workouts', 'activity')
    """
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    xml_path = str(xml_path)

    # Default to all types if none specified
    if types is None:
        types = ['records', 'workouts', 'activity']

    total_records = 0

    # Extract Records
    if 'records' in types:
        count = extract_with_progress(
            parse_records,
            xml_path,
            str(output_path / 'health_records.csv'),
            'health records'
        )
        total_records += count

    # Extract Workouts
    if 'workouts' in types:
        count = extract_with_progress(
            parse_workouts,
            xml_path,
            str(output_path / 'workouts.csv'),
            'workouts',
            progress_interval=1000
        )
        total_records += count

    # Extract Activity Summary
    if 'activity' in types:
        count = extract_with_progress(
            parse_activity_summary,
            xml_path,
            str(output_path / 'activity_summary.csv'),
            'activity summaries',
            progress_interval=1000
        )
        total_records += count

    print(f"\nDone! Extracted {total_records:,} total records.")


def main():
    parser = argparse.ArgumentParser(
        description='Extract Apple HealthKit data from XML export to CSV files.',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    # Extract all data types
    python extract_healthkit.py data/raw_health_export.xml --output data/

    # Extract only health records
    python extract_healthkit.py data/raw_health_export.xml --output data/ --types records

    # Extract records and workouts
    python extract_healthkit.py data/raw_health_export.xml --output data/ --types records workouts
        """
    )

    parser.add_argument(
        'xml_file',
        help='Path to the HealthKit export XML file'
    )

    parser.add_argument(
        '--output', '-o',
        default='.',
        help='Output directory for CSV files (default: current directory)'
    )

    parser.add_argument(
        '--types', '-t',
        nargs='+',
        choices=['records', 'workouts', 'activity'],
        help='Types of data to extract (default: all)'
    )

    args = parser.parse_args()

    # Validate input file exists
    if not Path(args.xml_file).exists():
        print(f"Error: File not found: {args.xml_file}")
        return 1

    extract_all(args.xml_file, args.output, args.types)
    return 0


if __name__ == '__main__':
    exit(main())
