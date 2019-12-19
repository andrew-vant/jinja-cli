#!/usr/bin/env python3

'''
main module;
'''

from jinja2 import DictLoader
from jinja2 import Environment
from jinja2 import FileSystemLoader
from jinja2 import Template
from os.path import basename
from os.path import dirname
import argparse
import argparse_ext
import configparser
import json
import logging
import os
import sys
import xmltodict
import yaml

##  program name;
prog = 'jinja'

logging.basicConfig(level=logging.INFO)

def load_data_ini(fin):

    '''
    load data in ini format;

    ##  params

    fin:file object
    :   data file object;

    ##  return

    :dict
    :   data;
    '''

    cp = configparser.ConfigParser()
    cp.read_file(fin)
    return { s: dict(cp.defaults(), **cp[s]) for s in cp.sections() }

def load_data_json(fin):

    '''
    load data in json format;

    ##  params

    fin:file object
    :   data file object;

    ##  return

    :dict
    :   data;
    '''

    return json.load(fin)

def load_data_xml(fin):

    '''
    load data in xml format;

    ##  params

    fin:file object
    :   data file object;

    ##  return

    :dict
    :   data;
    '''

    return xmltodict.parse(fin.read())

def load_data_yaml(fin):

    '''
    load data in yaml format;

    ##  params

    fin:file object
    :   data file object;

    ##  return

    :dict
    :   data;
    '''

    return yaml.safe_load(fin)


def load_data_dsv(fin, dialect='excel', has_headers=True):
    '''
    load delimiter-separated-values data;

    ##  params

    fin:file object
    :   data file object;
    dialect:str;
    :   name of registered csv dialect
    has_headers:str;
    :   whether columns have headers
    '''

    # Register a couple dialects of our own. User can pass in any of
    # the builtin dialects too.
    default_dialect_args = dict(
        quoting=csv.QUOTE_NONE,
        escapechar='\\',
        strict=True
        )
    csv.register_dialect('tsv', delimiter='\t', **dialect_args)
    csv.register_dialect('csv', delimiter=',', **dialect_args)

    cls_reader = csv.DictReader if has_headers else csv.reader
    reader = cls_reader(fin, dialect=dialect, **dialect_options)
    return list(reader)


def load_data(fname, fmt, defines):

    '''
    load data;

    ##  params

    fname:str
    :   data file name;
    fmt:str
    :   data format;
    defines:list
    :   data defined as command line arguments;

    ##  return

    :dict
    :   data;
    '''

    data = {}

    if fname is not None:
        ##  get input file object;
        if fname == '-':
            fin = sys.stdin
        else:
            fin = open(fname, 'rt')

        try:
            ##  detect data format;
            if fmt is None:
                if fname.endswith('.ini'):
                    fmt = 'ini'
                elif fname.endswith('.json'):
                    fmt = 'json'
                elif fname.endswith('.xml'):
                    fmt = 'xml'
                elif fname.endswith('.yaml'):
                    fmt = 'yaml'
                elif fname.endswith('.tsv'):
                    fmt = 'tsv'
                elif fname.endswith('.csv'):
                    fmt = 'csv'
                else:
                    raise Exception('no data format;')

            ##  load data;
            if fmt == 'ini':
                data = load_data_ini(fin)
            elif fmt == 'json':
                data = load_data_json(fin)
            elif fmt == 'xml':
                data = load_data_xml(fin)
            elif fmt == 'yaml':
                data = load_data_yaml(fin)
            elif fmt == 'tsv':
                data = load_data_dsv(fin, dialect='tsv')
            elif fmt == 'csv':
                data = load_data_dsv(fin, dialect='csv')
            elif fmt.startswith('csv.'):
                # allows the use of arbitrary stdlib csv dialects
                dialect = fmt.partition('.')[-1]
                data = load_data_dsv(fin, dialect)
            else:
                raise Exception('invalid data format: {};'.format(fmt))

        finally:
            fin.close()

    # csv/tsv return a list of dicts rather than a single dict, but the
    # jinja context expects a dict, so make it one if necessary. (this
    # will also work for json/yaml if the top-level structure isn't a
    # dict)

    if not isinstance(data, collections.Mapping):
        top_key = 'data'
        msg = "input doesn't provide top-level keys; using '%s'"
        logging.info(msg, top_key)
        data = {top_key: data}

    ##  merge in command line data;
    if defines is not None:
        data.update(defines)

    return data

def parse_args():

    '''
    parse command line arguments;
    '''

    ##  init arg parser;
    parser = argparse.ArgumentParser(
        prog=prog,
        description='a command line interface to jinja;',
        formatter_class=argparse_ext.HelpFormatter,
        add_help=False,
    )

    ##  add arg;
    parser.add_argument(
        '-h', '--help',
        action='help',
        help='display help message;',
    )

    ##  add arg;
    parser.add_argument(
        '-D', '--define',
        action='append',
        nargs=2,
        type=str,
        metavar=('key', 'value'),
        help='define data;',
    )

    ##  add arg;
    parser.add_argument(
        '-d', '--data',
        type=str,
        metavar='file',
        help='data file;',
    )

    ##  add arg;
    parser.add_argument(
        '-f', '--format',
        type=str,
        metavar='format',
        help='data format;',
    )

    ##  add arg;
    parser.add_argument(
        '-o', '--output',
        type=str,
        metavar='file',
        help='output file;',
    )

    ##  add arg;
    parser.add_argument(
        'template',
        nargs='?',
        type=str,
        metavar='template',
        help='template file;',
    )

    ##  parse args;
    args = parser.parse_args()

    return args

def main():

    '''
    main function;
    '''

    ##  parse args;
    args = parse_args()

    ##  load template;
    if args.template is None or args.template == '-':
        env = Environment(
            loader=DictLoader({ '-': sys.stdin.read() }),
            keep_trailing_newline=True,
        )
        template = env.get_template('-')
    else:
        env = Environment(
            loader=FileSystemLoader(dirname(args.template)),
            keep_trailing_newline=True,
        )
        template = env.get_template(basename(args.template))

    ##  load data;
    data = load_data(args.data, args.format, args.define)

    ##  render template with data;
    rendered = template.render(data)

    ##  write to output;
    if args.output is None or args.output == '-':
        fout = sys.stdout
    else:
        fout = open(args.output, 'wt')
    try:
        fout.write(rendered)
    finally:
        fout.close()

if __name__ == '__main__':
    main()

