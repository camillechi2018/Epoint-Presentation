"""Guard slide inheritance and editability when consolidating cloned designs."""
import sys
import tempfile
import unittest
from pathlib import Path
from zipfile import ZipFile

from pptx import Presentation
from pptx.opc.constants import RELATIONSHIP_TYPE as RT
from pptx.util import Inches

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from assemble_native import assemble_many
from delivery_gate import check_package_relations
from optimize_masters import optimize


class MasterOptimizationTests(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.root = Path(directory.name)

    def source(self, name, layout_index, *, other_layout=False, other_theme=False):
        deck = Presentation()
        if other_layout:
            # A layout not used by this sample slide remains available to editors.
            deck.slide_layouts[8]._element.cSld.set('name', 'Keep this layout')
        if other_theme:
            theme = deck.slide_masters[0].part.part_related_by(RT.THEME)
            self.assertIn(b'4F81BD', theme.blob)
            theme.blob = theme.blob.replace(b'4F81BD', b'010203')
        slide = deck.slides.add_slide(deck.slide_layouts[layout_index])
        slide.shapes.add_textbox(Inches(1), Inches(1), Inches(1), Inches(1)).text = name
        path = self.root / f'{name}.pptx'
        deck.save(path)
        return path

    def test_clones_share_master_while_each_slide_keeps_its_layout(self):
        sources = [self.source('first', 1), self.source('second', 5)]
        result = self.root / 'result.pptx'
        assemble_many(sources, result)
        with ZipFile(result) as archive:
            slide_parts = {path: archive.read(path) for path in archive.namelist()
                           if path.startswith('ppt/slides/slide') and path.endswith('.xml')}
        report = optimize(result)
        self.assertEqual((report['masters_before'], report['masters_after']), (2, 1))
        deck = Presentation(result)
        self.assertEqual(len(deck.slide_masters), 1)
        self.assertEqual([slide.slide_layout.name for slide in deck.slides], ['Title and Content', 'Title Only'])
        self.assertEqual([slide.shapes[-1].text for slide in deck.slides], ['first', 'second'])
        self.assertEqual(len(deck.slide_masters[0].slide_layouts), 11)
        self.assertEqual(check_package_relations(result)['status'], 'passed')
        with ZipFile(result) as archive:
            self.assertEqual({path: archive.read(path) for path in slide_parts}, slide_parts)
        before = result.read_bytes()
        self.assertEqual(optimize(result)['removed_parts'], 0)
        self.assertEqual(result.read_bytes(), before)

    def test_distinct_theme_and_unused_editing_layout_keep_separate_masters(self):
        sources = [self.source('first', 1), self.source('layout', 1, other_layout=True),
                   self.source('theme', 1, other_theme=True)]
        result = self.root / 'result.pptx'
        assemble_many(sources, result)
        self.assertEqual(optimize(result)['masters_after'], 3)
        self.assertEqual(check_package_relations(result)['status'], 'passed')
