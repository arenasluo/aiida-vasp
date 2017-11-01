"""Unittests for the PymatgenParser"""
# pylint: disable=unused-import,redefined-outer-name,unused-argument,unused-wildcard-import,wildcard-import
import os

import pytest
from aiida.common.exceptions import ParsingError

from aiida_vasp.parsers.pymatgen_vasp import PymatgenParser
from aiida_vasp.utils.fixtures import *


def data_path(*args):
    """path to a test data file"""
    path = os.path.realpath(
        os.path.join(__file__, '../../../test_data', *args))
    assert os.path.exists(path)
    assert os.path.isabs(path)
    return path


@pytest.fixture(params=[-1])
def vasprun_path(request, tmpdir):
    """Truncate vasprun.xml at the given line number and parse"""
    original_path = data_path('phonondb', 'vasprun.xml')
    if request.param == -1:
        return original_path
    truncated_path = tmpdir.join('vasprun.xml')
    with open(original_path, 'r') as original_fo:
        truncated_content = '\n'.join(original_fo.readlines()[:request.param])
    truncated_path.write(truncated_content)
    return str(truncated_path)


@pytest.fixture(params=[None])
def parse_result(request, aiida_env, vasprun_path):
    """
    Result of parsing a retrieved calculation (emulated)

    1. create a calculation with parser settings
    2. create a parser with the calculation
    3. populate a fake retrieved folder and pass it to the parser
    """
    from aiida.orm import CalculationFactory, DataFactory
    calc = CalculationFactory('vasp.vasp')()
    calc.use_settings(
        DataFactory('parameter')(dict={
            'pymatgen_parser': {
                'parse_potcar_file': False,
                'exception_on_bad_xml': request.param
            }
        }))
    parser = PymatgenParser(calc=calc)
    retrieved = DataFactory('folder')()
    retrieved.add_path(vasprun_path, '')

    def parse():
        return parser.parse_with_retrieved({'retrieved': retrieved})

    return parse


def test_kpoints_result(parse_result):
    from aiida.orm import DataFactory
    _, nodes = parse_result()
    nodes = dict(nodes)
    assert isinstance(nodes['kpoints'], DataFactory('array.kpoints'))


def test_structure_result(parse_result):
    from aiida.orm import DataFactory
    _, nodes = parse_result()
    nodes = dict(nodes)
    assert isinstance(nodes['structure'], DataFactory('structure'))


@pytest.mark.parametrize(
    ['vasprun_path', 'parse_result'], [(2331, False)], indirect=True)
def test_slightly_broken_vasprun(parse_result, recwarn):
    """Test that truncated vasprun (after one ionic step) can be read and warnings are emitted"""
    success, nodes = parse_result()
    nodes = dict(nodes)
    assert success
    assert 'kpoints' in nodes
    assert 'structure' in nodes
    assert len(recwarn) >= 1


@pytest.mark.parametrize(
    ['vasprun_path', 'parse_result'], [(2331, True)], indirect=True)
def test_broken_vasprun_exception(parse_result):
    with pytest.raises(ParsingError):
        _ = parse_result()