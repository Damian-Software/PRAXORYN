#!/usr/bin/env python3
"""Calculate an idealized KV-cache memory budget, not observed VRAM usage."""
import argparse


def kv_bytes(layers: int, kv_heads: int, head_dim: int, context: int,
             bytes_per_value: int, sequences: int) -> int:
    values = (layers, kv_heads, head_dim, context, bytes_per_value, sequences)
    if any(type(value) is not int or value <= 0 for value in values):
        raise ValueError('All parameters must be positive integers')
    return 2 * layers * kv_heads * head_dim * context * bytes_per_value * sequences


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--layers', required=True, type=int)
    parser.add_argument('--kv-heads', required=True, type=int)
    parser.add_argument('--head-dim', required=True, type=int)
    parser.add_argument('--context', required=True, type=int)
    parser.add_argument('--bytes-per-value', required=True, type=int)
    parser.add_argument('--sequences', required=True, type=int)
    args = parser.parse_args()
    value = kv_bytes(args.layers, args.kv_heads, args.head_dim, args.context,
                     args.bytes_per_value, args.sequences)
    print('bytes:', value)
    print('GiB:', f'{value / 1024**3:.4f}')


if __name__ == '__main__':
    main()
