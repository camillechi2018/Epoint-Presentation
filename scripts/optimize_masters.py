"""Consolidate equivalent slide masters after page-level repairs are complete."""
from __future__ import annotations

import argparse
import hashlib
import json
import posixpath
import re
import shutil
import tempfile
from pathlib import Path
from urllib.parse import quote
from zipfile import ZipFile

from lxml import etree

from opc_relationships import rels_name, resolve_target

P = '{http://schemas.openxmlformats.org/presentationml/2006/main}'
R = '{http://schemas.openxmlformats.org/officeDocument/2006/relationships}'
A = '{http://schemas.openxmlformats.org/drawingml/2006/main}'
P14 = '{http://schemas.microsoft.com/office/powerpoint/2010/main}'
SLIDE_LAYOUT = R[1:-1] + '/slideLayout'
SLIDE_MASTER = R[1:-1] + '/slideMaster'
SLIDE = R[1:-1] + '/slide'
THEME = R[1:-1] + '/theme'
PRESENTATION = 'ppt/presentation.xml'
CONTENT_TYPES = '[Content_Types].xml'


class UnsupportedMaster(ValueError):
    """A dependency cannot be safely compared or mapped to the retained master."""


class Package:
    def __init__(self, archive):
        self.archive = archive
        names = [info.filename for info in archive.infolist() if not info.is_dir()]
        self.parts = set(names)
        if len(self.parts) != len(names):
            raise ValueError('DUPLICATE_PACKAGE_PART')
        self.changed = {}
        self.removed = set()
        self.relationships = {}
        self.types = self.xml(CONTENT_TYPES)
        self.overrides = {resolve_target('', node.get('PartName')): node.get('ContentType')
                          for node in self.types if node.get('PartName')}
        self.defaults = {node.get('Extension').lower(): node.get('ContentType')
                         for node in self.types if node.get('Extension')}

    def xml(self, part):
        return etree.fromstring(self.archive.read(part))

    def rels(self, owner):
        if owner not in self.relationships:
            name = rels_name(owner)
            self.relationships[owner] = self.xml(name) if name in self.parts else None
        root = self.relationships[owner]
        return {node.get('Id'): node for node in root} if root is not None else {}

    def save_xml(self, part, node):
        self.changed[part] = etree.tostring(node, encoding='UTF-8', xml_declaration=True, standalone=True)

    def save_rels(self, owner):
        self.save_xml(rels_name(owner), self.relationships[owner])

    def ordered(self, owner, root, list_tag, kind):
        entries = root.find(f'{P}{list_tag}')
        if entries is None:
            return []
        rels = self.rels(owner)
        result = []
        for node in entries:
            rel = rels[node.get(f'{R}id')]
            if rel.get('Type') != kind or rel.get('TargetMode') == 'External':
                raise ValueError(f'INVALID_PRESENTATION_RELATIONSHIP: {owner} {list_tag}')
            result.append((node, rel, self.target(owner, rel)))
        return result

    @staticmethod
    def target(owner, rel):
        return resolve_target(owner, rel.get('Target'))

    def reach(self, roots):
        reached = set()
        pending = list(roots)
        while pending:
            owner = pending.pop()
            if owner in reached:
                continue
            reached.add(owner)
            for rel in self.rels(owner).values():
                if rel.get('TargetMode') != 'External':
                    target = self.target(owner, rel)
                    if target in self.parts:
                        pending.append(target)
        return reached

    def remove_unreachable(self, candidates):
        # Keep every dependency of the document and of any unrelated package part.
        owners = {p for p in self.parts if not p.endswith('.rels')}
        orphaned = candidates - self.reach((owners - candidates) | {''})
        self.removed.update(orphaned)
        self.removed.update(rels_name(part) for part in orphaned)
        for node in list(self.types):
            path = node.get('PartName')
            if path and resolve_target('', path) in orphaned:
                self.types.remove(node)
        self.save_xml(CONTENT_TYPES, self.types)

    def write(self, output):
        with ZipFile(output, 'w') as dest:
            dest.comment = self.archive.comment
            for info in self.archive.infolist():
                if info.filename not in self.removed:
                    data = self.changed.get(info.filename)
                    dest.writestr(info, self.archive.read(info) if data is None else data)


class MasterSignatures:
    def __init__(self, package, office_clones):
        self.package = package
        self.office_clones = office_clones
        self.cache = {}

    def signature(self, part, role, ancestors=()):
        key = (part, role)
        if key in self.cache:
            return self.cache[key]
        if part in ancestors or part not in self.package.parts:
            raise UnsupportedMaster(f'Unresolved or circular dependency: {part}')

        contents = self.package.archive.read(part)
        xml = etree.fromstring(contents) if role in ('master', 'layout', 'theme') else None
        extension = posixpath.splitext(part)[1][1:].lower()
        content_type = self.package.overrides.get(part, self.package.defaults.get(extension))
        relations = []
        reference_ids = {}
        for rid, rel in self.package.rels(part).items():
            kind = rel.get('Type')
            if role == 'layout' and kind == SLIDE_MASTER:
                continue
            external = rel.get('TargetMode') == 'External'
            if external:
                target = rel.get('Target')
            else:
                target_part = self.package.target(part, rel)
                dependency_role = 'layout' if role == 'master' and kind == SLIDE_LAYOUT else 'opaque'
                if role == 'master' and kind == THEME:
                    dependency_role = 'theme'
                target = self.signature(target_part, dependency_role, (*ancestors, part))
            descriptor = (tuple(sorted((k, v) for k, v in rel.attrib.items() if k not in ('Id', 'Target'))), target)
            if xml is None:
                # Opaque part bytes still reference their original relationship IDs.
                descriptor = (rid, *descriptor)
            reference_ids[rid] = hashlib.sha256(repr(descriptor).encode()).hexdigest()
            relations.append(descriptor)

        if xml is not None:
            if role == 'master':
                for entry in xml.findall(f'{P}sldLayoutIdLst/{P}sldLayoutId'):
                    entry.set('id', '0')
            if self.office_clones:
                # PowerPoint generates new design IDs and a display-name prefix on Clone().
                if role in ('master', 'layout'):
                    for node in xml.findall(f'{P}cSld/{P}extLst/{P}ext/{P14}creationId'):
                        if node.get('val', '').isdigit():
                            node.set('val', '0')
                if role == 'theme' and xml.tag == f'{A}theme' and xml.get('name'):
                    xml.set('name', re.sub(r'^\d+_', '', xml.get('name')))
            for element in xml.iter():
                for attr, value in element.attrib.items():
                    if attr.startswith(R) and value in reference_ids:
                        element.set(attr, reference_ids[value])
            contents = etree.tostring(xml, method='c14n', with_comments=False)

        descriptor = (content_type, tuple(sorted(relations)), hashlib.sha256(contents).hexdigest())
        signature = hashlib.sha256(repr(descriptor).encode()).hexdigest()
        self.cache[key] = signature
        return signature

    def layouts(self, master):
        layout_rows = self.package.ordered(master, self.package.xml(master), 'sldLayoutIdLst', SLIDE_LAYOUT)
        layouts = [path for _, _, path in layout_rows]
        declared = [self.package.target(master, rel) for rel in self.package.rels(master).values()
                    if rel.get('Type') == SLIDE_LAYOUT and rel.get('TargetMode') != 'External']
        if not layouts or len(set(layouts)) != len(layouts) or sorted(layouts) != sorted(declared):
            raise UnsupportedMaster(f'Cannot map layout list for {master}')
        for layout in layouts:
            parents = [rel for rel in self.package.rels(layout).values()
                       if rel.get('Type') == SLIDE_MASTER]
            if (len(parents) != 1 or parents[0].get('TargetMode') == 'External'
                    or self.package.target(layout, parents[0]) != master):
                raise UnsupportedMaster(f'Cannot map master for {layout}')
        return layouts


def consolidate(package, office_clones):
    presentation = package.xml(PRESENTATION)
    masters = package.ordered(PRESENTATION, presentation, 'sldMasterIdLst', SLIDE_MASTER)
    signatures = MasterSignatures(package, office_clones)
    retained = {}
    duplicates = []
    replacement_layouts = {}
    for node, rel, master in masters:
        try:
            layouts = signatures.layouts(master)
            signature = signatures.signature(master, 'master')
        except UnsupportedMaster:
            continue
        if signature not in retained:
            retained[signature] = (master, layouts)
            continue
        keep, keep_layouts = retained[signature]
        if keep == master or master in (item[2] for item in duplicates):
            raise ValueError(f'DUPLICATE_MASTER_REGISTRATION: {master}')
        replacement_layouts.update(zip(layouts, keep_layouts, strict=True))
        duplicates.append((node, rel, master))

    if duplicates:
        for _, _, slide in package.ordered(PRESENTATION, presentation, 'sldIdLst', SLIDE):
            for rel in package.rels(slide).values():
                if rel.get('Type') != SLIDE_LAYOUT or rel.get('TargetMode') == 'External':
                    continue
                replacement = replacement_layouts.get(package.target(slide, rel))
                if replacement:
                    rel.set('Target', quote(posixpath.relpath(replacement, posixpath.dirname(slide))))
                    package.save_rels(slide)
        candidates = package.reach(master for _, _, master in duplicates)
        for node, rel, _ in duplicates:
            node.getparent().remove(node)
            rel.getparent().remove(rel)
        package.save_xml(PRESENTATION, presentation)
        package.save_rels(PRESENTATION)
        package.remove_unreachable(candidates)

    return {'masters_before': len(masters), 'masters_after': len(masters) - len(duplicates),
            'removed_parts': len(package.parts & package.removed)}


def optimize(source, output=None, *, office_clones=False):
    source = Path(source).resolve()
    output = Path(output).resolve() if output is not None else source
    # The archive is closed before replacement so this works with Windows file locking.
    with tempfile.TemporaryDirectory(prefix='.masters-', dir=output.parent) as directory:
        candidate = Path(directory) / output.name
        with ZipFile(source) as archive:
            package = Package(archive)
            report = consolidate(package, office_clones)
            if package.changed:
                package.write(candidate)
        if candidate.exists():
            candidate.replace(output)
        elif source != output:
            shutil.copyfile(source, output)
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input', type=Path, required=True)
    parser.add_argument('--out', type=Path)
    parser.add_argument('--office-clones', action='store_true')
    parser.add_argument('--report', type=Path)
    args = parser.parse_args()
    result = optimize(args.input, args.out, office_clones=args.office_clones)
    if args.report:
        args.report.write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(result))


if __name__ == '__main__':
    main()
