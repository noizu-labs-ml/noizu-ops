import os
import argparse
import smah.smah_config

def extract_args():
    parser = argparse.ArgumentParser(description="SMAH Command Line Tool")
    parser.add_argument('-q', '--query', type=str, help='Query to answer')
    parser.add_argument('--config', type=str, help='Path to alternative config file')
    args = parser.parse_args()
    return parser, args

def main():
    parser, args = extract_args()
    config = smah.smah_config.Config(config=args.config)
    if not config.configured():
        config.configure()
    print (f"Configured: {config.version}")




