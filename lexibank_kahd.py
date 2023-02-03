import attr
from pathlib import Path
import subprocess

from pylexibank import Concept, Language, Cognate, Lexeme
from pylexibank.dataset import Dataset as BaseDataset
from pylexibank.util import progressbar
from csvw import Datatype
from pyclts import CLTS
try:
    from pytular.util import fetch_sheet
except ImportError:
    fetch_sheet = None


import lingpy
from clldutils.misc import slug

@attr.s
class CustomConcept(Concept):
    Number = attr.ib(default=None)
    Semantic_Field = attr.ib(default=None)

@attr.s
class CustomLanguage(Language):
    Latitude = attr.ib(default=None)
    Longitude = attr.ib(default=None)
#   SubGroup = attr.ib(default=None)
    Source = attr.ib(default=None)

@attr.s
class CustomCognate(Cognate):
    Segment_Slice = attr.ib(default=None)


@attr.s
class Form(Lexeme):
    Morphemes = attr.ib(default=None)
    SimpleCognate = attr.ib(default=None)
    PartialCognates = attr.ib(default=None)


class Dataset(BaseDataset):
    dir = Path(__file__).parent
    id = "kahd"
    concept_class = CustomConcept
    language_class = CustomLanguage
    cognate_class = CustomCognate
    lexeme_class = Form

    def cmd_download(self, args):
        print('updating ...')
        self.raw_dir.download(
            "https://lingulist.de/edictor/triples/get_data.py?file=arawa&remote_dbase=arawa.sqlite3",
            "arawa.tsv"
        )
        print('... arawa.tsv done')
        subprocess.check_call(
            'git -C {} submodule update --remote'.format(self.dir.resolve()), shell=True)
        print('... sources.bib done')
        fetch_sheet('arawa_languages', output=self.etc_dir / 'languages.tsv')
        fetch_sheet('arawa_concepts', output=self.etc_dir / 'concepts.tsv')

    def cmd_makecldf(self, args):
        from pybtex import errors, database
        errors.strict = False
        bibdata = database.parse_file(str(self.raw_dir.joinpath('bibliography', 'sources.bib')))
        args.writer.add_sources(bibdata)
        args.writer["FormTable", "Segments"].datatype = Datatype.fromvalue(
            {"base": "string", "format": "([\\S]+)( [\\S]+)*"}
            )
        args.writer["FormTable", "Morphemes"].separator = " "
        args.writer["FormTable", "PartialCognates"].separator = " "

        concepts = {}
        errors, blacklist = set(), set()
        for concept in self.conceptlists[0].concepts.values():
            idx = "{0}_{1}".format(concept.number, slug(concept.english))
            args.writer.add_concept(
                    ID=idx,
                    Name=concept.english,
                    Concepticon_ID=concept.concepticon_id,
                    Concepticon_Gloss=concept.concepticon_gloss
                    )
            concepts[concept.english] = idx

        languages = {}
        sources = {}
        for row in self.languages:
            if not -90 < float(row['Latitude']) < 90:
                errors.add('LATITUDE {0}'.format(row['Name']))
            elif not -180 < float(row['Longitude']) < 180:
                errors.add('LONGITUDE {0}'.format(row['Name']))
            else:
                try:
                    args.writer.add_language(
                        ID=row['ID'],
                        Name=row['Name'],
                        Latitude=row['Latitude'],
                        Longitude=row['Longitude'],
                        Glottocode=row['Glottocode'] if row['Glottocode'] != '???' else None,
                    )
                    languages[row['Name']] = row['ID']
                    sources[row['Name']] = []
                    for source in row['Sources'].split(','):
                        if source in bibdata.entries:
                            sources[row['Name']] += [source]
                        else:
                            errors.add('BIBTEX MISSING {0}'.format(source))
                except ValueError:
                    errors.add('LANGUAGE ID {0}'.format(
                        row['ID'],
                        ))
                    args.log.warning('Invalid Language ID {0}'.format(row['ID']))

        wl = lingpy.Wordlist(self.raw_dir.joinpath('arawa.tsv').as_posix())
        etd = wl.get_etymdict(ref='cogids')
        alignments, problems = {}, set()
        for cogid, vals in progressbar(etd.items(), desc='aligning data'):
            idxs = []
            for idx in vals:
                if idx:
                    idxs += idx
            positions = [wl[idx, 'cogids'].index(cogid) for idx in idxs]
            alms, new_idxs = [], []
            for idx, pos in zip(idxs, positions):
                try:
                    tks = lingpy.basictypes.lists(wl[idx, 'tokens']).n[pos]
                    if not ' '.join(tks).strip():
                        raise IndexError
                    alms += [tks]
                    new_idxs += [(idx, pos)]
                except IndexError:
                    problems.add((idx, pos))
            if alms:
                msa = lingpy.Multiple(alms)
                msa.prog_align()
                for i, alm in enumerate(msa.alm_matrix):
                    alignments[new_idxs[i][0], new_idxs[i][1], cogid] = ' '.join(alm)
            else:
                errors.add('ALIGNMENT empty {0}'.format(cogid))

        bipa = CLTS(args.clts.dir).bipa
        for idx, tokens, glosses, cogids, alignment in wl.iter_rows(
                'tokens', 'morphemes', 'cogids', 'alignment'):
            tl, gl, cl, al = (
                    len(lingpy.basictypes.lists(tokens).n),
                    len(glosses),
                    len(cogids),
                    len(lingpy.basictypes.lists(alignment).n)
                    )
            if tl != gl or tl != cl or gl != cl or al != gl or al != cl:
                errors.add('LENGTH: {0} {1} {2}'.format(
                    idx,
                    wl[idx, 'language'],
                    wl[idx, 'concept']))
                blacklist.add(idx)
            for token in tokens:
                if bipa[token].type == 'unknownsound':
                    errors.add('SOUND: {0}'.format(token))
                    blacklist.add(idx)

        visited = set()
        for idx in wl:
            if wl[idx, 'concept'] not in concepts:
                if wl[idx, 'concept'] not in visited:
                    args.log.warning('Missing concept {0}'.format(wl[idx,
                    'concept']))
                    visited.add(wl[idx, 'concept'])
                    errors.add('CONCEPT {0}'.format(wl[idx, 'concept']))
            elif wl[idx, 'doculect'] not in languages:
                if wl[idx, 'doculect'] not in visited:
                    args.log.warning("Missing language {0}".format(wl[idx, 'doculect']
                        ))
                    visited.add(wl[idx, 'doculect'])
                    errors.add('LANGUAGE {0}'.format(wl[idx, 'doculect']))
            else:
                if ''.join(wl[idx, 'tokens']).strip() and idx not in blacklist:
                    lex = args.writer.add_form_with_segments(
                        Language_ID=languages[wl[idx, 'doculect']],
                        Parameter_ID=concepts[wl[idx, 'concept']],
                        Value=wl[idx, 'value'] or ''.join(wl[idx, 'tokens']),
                        Form=wl[idx, 'form'] or ''.join(wl[idx, 'tokens']),
                        Segments=wl[idx, 'tokens'],
                        Morphemes=wl[idx, 'morphemes'],
                        SimpleCognate=wl[idx, 'cogid'],
                        PartialCognates=wl[idx, 'cogids'],
                        Source=sources[wl[idx, 'doculect']],
                    )
                    for gloss_index, cogid in enumerate(wl[idx, 'cogids']):
                        args.writer.add_cognate(
                                lexeme=lex,
                                Cognateset_ID=cogid,
                                Segment_Slice=gloss_index+1,
                                Alignment=alignments.get(
                                    (idx, gloss_index, cogid),
                                    ''),
                                Alignment_Method='SCA'
                                )
                else:
                    args.log.warning('Entry ID={0}, concept={1}, language={2} is empty'.format(
                        idx, wl[idx, 'concept'], wl[idx, 'doculect']))
        

        with open(self.dir.joinpath('errors.md'), 'w', encoding="utf-8") as f:
            f.write('# Error Analysis for ARAWA\n')
            for error in sorted(errors):
                f.write('* '+error+'\n')
