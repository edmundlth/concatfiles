import pathlib

from concat_files import should_include_file


def test_inclusion_with_include_set():
    path = pathlib.Path('example.txt')
    include = {'txt', 'md'}
    assert should_include_file(path, include, None) is True


def test_exclusion_with_exclude_set():
    path = pathlib.Path('example.log')
    exclude = {'log', 'tmp'}
    assert should_include_file(path, None, exclude) is False


def test_include_and_exclude_sets():
    include = {'txt', 'md'}
    exclude = {'md'}
    path_md = pathlib.Path('doc.md')
    path_txt = pathlib.Path('doc.txt')

    # File extension present in both include and exclude -> excluded
    assert should_include_file(path_md, include, exclude) is False
    # File extension only in include -> included
    assert should_include_file(path_txt, include, exclude) is True
