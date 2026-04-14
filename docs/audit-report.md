# Rapport d'audit — sorting-algorithms

Audit exhaustif read-only du projet `sorting-algorithms` (Papyrus de Héron).
Date : 2026-04-14. Baseline tests : 76/76 verts.

## Outillage utilisé

- `ruff check` (lint)
- `mypy --ignore-missing-imports` (types)
- `bandit -r` (sécurité)
- `vulture` (code mort)
- `pip-audit -r requirements.txt` (CVE deps projet) → **0 CVE**
- `radon cc -s -a -n C` + `radon mi -s -n B` (complexité, maintenabilité)
- Revue manuelle par agents Explore parallèles (algorithms/main/tests, benchmarks, visualization)

## Synthèse

- **Scope** : 7020 LOC Python sur 30+ fichiers
- **Total findings retenus** : 34 (après élimination des faux positifs)
  - **Critique** : 2
  - **Majeur** : 15
  - **Mineur** : 14
  - **Cosmétique** : 3
- **Zones les plus touchées** : `visualization/app.py::run_race` (threading pygame), `benchmarks/database.py` (fuite connexions), `benchmarks/runner.py` (métriques corrompues)
- **Deps projet** : aucune CVE

## Faux positifs écartés

- **Bandit B311** (12 occurrences) : `random.random()` / `random.shuffle` utilisés pour générer des datasets pédagogiques, jamais pour de la crypto. Non pertinent.
- **Bandit B608** `benchmarks/database.py:162` : `agg_fn` et `col` sont issus de dictionnaires à clés whitelistées, un `KeyError` est levé avant toute exécution SQL. Pas d'injection possible en l'état.
- **Mypy** `quick.py:209/214` et `comb.py:220` (None safety sur fonts) : protection amont effective via lazy init dans `draw()`. Signalés en Mineur malgré tout car fragiles.
- **Mypy** `score_screen.py:157` : `vals` filtré et non-vide avant appel à `min`/`max`. Faux positif structurel.
- **Agent 1 FINDING 1 initial** (comb_sort.py) : convergence prouvée par revue manuelle.

---

## Findings Critiques

### AUDIT-01 — Race condition `states["steps"] += 1`
- **Fichier** : `visualization/app.py:422-424`
- **Catégorie** : runtime
- **Preuve** : Les threads race écrivent `states[algo]["steps"] += 1` sans verrou. L'opération `+=` sur int est un read-modify-write non atomique. Un commentaire prétend à tort que c'est sûr car "Python exécute un bytecode à la fois".
- **Impact** : Compteurs incorrects (perte d'incréments) ; bug structurel, deviendra un vrai crash sous Python 3.13 free-threaded.
- **Reco** : Remplacer par un verrou par slot, ou un `itertools.count`/`queue.Queue` pour la communication.

### AUDIT-02 — Lecture incohérente `arr`/`highlighted` depuis le main thread
- **Fichier** : `visualization/app.py:422-423` (écriture), `:831`/`:876` (lecture)
- **Catégorie** : runtime
- **Preuve** : Les threads écrivent successivement `states[algo]["arr"] = arr` puis `states[algo]["highlighted"] = (i, j, event_type)` sans synchronisation. Le main thread peut lire un `arr` ancien et un `highlighted` frais (ou inverse), puis passer `s["arr"][i]` à un renderer où `i` dépasse `len(arr)`.
- **Impact** : `IndexError` intermittent dans n'importe quel renderer pendant une course, reproductible plus facilement avec N élevé et vitesse basse.
- **Reco** : Construire un snapshot local `{"arr": ..., "highlighted": ...}` et l'affecter en une seule écriture à `states[algo]`, ou introduire un verrou par slot.

---

## Findings Majeurs

### AUDIT-03 — `run_benchmark` ne copie pas le tableau entre algos
- **Fichier** : `benchmarks/runner.py:20`
- **Catégorie** : correction / perf
- **Preuve** : `fn(arr, on_step=on_step)` passe le tableau original à chaque tri. Les tris en place (bubble, insertion, selection…) le modifient, donc les algos suivants reçoivent un tableau déjà trié.
- **Impact** : Métriques `comparisons`/`swaps`/`time` corrompues pour tous les algos sauf le premier. Invalide le cœur pédagogique.
- **Reco** : `fn(list(arr), on_step=on_step)` comme dans `run_full_benchmark`.

### AUDIT-04 — Fuites systématiques de connexions SQLite
- **Fichier** : `benchmarks/database.py:53-55, 91-109, 116-123, 132-143, 160-167, 173-194, 200-202, 207-210, 215-219`
- **Catégorie** : runtime
- **Preuve** : Pattern `conn = _connect(...); ...; conn.close()` sans `try/finally` ni `with`. Toute exception entre ouverture et fermeture laisse le fichier `.db` verrouillé.
- **Impact** : Fuite FD, verrou persistant indéterministe, tests pytest qui se gênent entre eux.
- **Reco** : Centraliser via un context manager `@contextmanager def _db(path)`.

### AUDIT-05 — Transaction non atomique dans `import_legacy_json`
- **Fichier** : `benchmarks/database.py:91-109`
- **Catégorie** : runtime
- **Preuve** : Session insérée puis `executemany` sur les runs, sans transaction explicite. Si `executemany` échoue, la session reste orpheline.
- **Impact** : Base incohérente avec sessions sans runs.
- **Reco** : Utiliser `with conn:` (auto-commit/rollback) autour du bloc session+runs.

### AUDIT-06 — `except Exception: pass` dans la boucle d'import legacy
- **Fichier** : `benchmarks/database.py:67-68`
- **Catégorie** : runtime
- **Preuve** : Toute erreur d'import (JSON corrompu, permissions, contrainte SQL) est silencieusement avalée.
- **Impact** : Imports partiels sans aucun signal à l'utilisateur.
- **Reco** : Logger l'exception, remonter éventuellement une liste de résultats.

### AUDIT-07 — Fuite de connexion dans `export_csv`
- **Fichier** : `benchmarks/exporter.py:26-58`
- **Catégorie** : runtime
- **Preuve** : `conn = _connect(...)`, itération du curseur à l'intérieur d'un `with open(...)`, puis `conn.close()`. Toute exception I/O laisse la connexion ouverte.
- **Reco** : `with` sur la connexion ; idéalement `cursor.fetchall()` avant d'ouvrir le fichier.

### AUDIT-08 — Fuite de connexion dans `export_pdf`
- **Fichier** : `benchmarks/exporter.py:75-150`
- **Catégorie** : runtime
- **Preuve** : Même pattern sans `try/finally`.
- **Reco** : Idem AUDIT-04.

### AUDIT-09 — `pygame.mixer.init` manquant dans `run_race`
- **Fichier** : `visualization/app.py:517`
- **Catégorie** : runtime
- **Preuve** : `run()` appelle explicitement `pygame.mixer.init(44100, -16, 2)` (ligne 197) mais `run_race()` se contente de `pygame.init()`. `audio.generate_tones` peut alors crasher avec `pygame.error: mixer not initialized`, masqué par un `except Exception: pass` global.
- **Impact** : Son en mode race totalement désactivé en silence, ou crash selon timing.
- **Reco** : Extraire une fonction `_init_audio()` partagée par `run` et `run_race`.

### AUDIT-10 — `stop_flag` non vérifié pendant `time.sleep`
- **Fichier** : `visualization/app.py:418` (approx.)
- **Catégorie** : runtime / UX
- **Preuve** : Chaque thread de course dort `time.sleep(speed[0])` après la dernière vérification de `stop_flag`. À vitesse lente (1s), la fermeture ou le changement de dataset attend jusqu'à 1 seconde par thread.
- **Impact** : Freeze UI de 1-2 secondes à chaque `arreter_threads`.
- **Reco** : Utiliser `stop_flag.wait(timeout=speed[0])` au lieu de `time.sleep`, ou découper le sleep.

### AUDIT-11 — Benchmark synchrone dans le main thread (score_screen)
- **Fichier** : `visualization/score_screen.py:714-766`
- **Catégorie** : UX
- **Preuve** : `run_full_benchmark()` est appelé dans le main thread avec un callback `on_progress` qui pompe les events uniquement à chaque run terminé. Entre deux runs (N=1000 + bubble, plusieurs secondes), la fenêtre ne répond pas.
- **Impact** : Freeze UI perceptible, l'OS peut marquer la fenêtre "not responding".
- **Reco** : Déplacer le benchmark dans un thread worker avec `queue.Queue` pour les updates.

### AUDIT-12 — Logique d'annulation incorrecte dans `_start_benchmark`
- **Fichier** : `visualization/score_screen.py:755` (approx.)
- **Catégorie** : correction
- **Preuve** : La condition `if self._progress_cancelled and i >= self._progress_current` compare l'index du résultat `i` avec un compteur de progression non corrélé. Résultats inclus/exclus de manière non déterministe.
- **Reco** : Clarifier le contrat d'annulation et utiliser un flag simple à vérifier entre chaque run.

### AUDIT-13 — Busy loop dans `_VIEW_PROGRESS`
- **Fichier** : `visualization/score_screen.py:812-820`
- **Catégorie** : perf
- **Preuve** : Le `clock.tick(FPS)` n'est appelé dans `on_progress`, pas dans la boucle externe en phase PROGRESS. Quand un run est long, la boucle principale spin à 100% CPU.
- **Reco** : Ajouter un throttle dans la boucle externe aussi pour cet état.

### AUDIT-14 — Crash `TypeError` sur preset `with_none`
- **Fichier** : `main.py:79-83, 97-99` + `algorithms/*.py`
- **Catégorie** : runtime
- **Preuve** : Le preset `"n"` (`with_none`) est exposé dans les modes CLI `--visual`/`--race`. Les 7 algos comparent `>` / `<=` sans gestion de `None` : `TypeError` garanti dès sélection.
- **Reco** : Soit filtrer `None` avant appel, soit retirer le preset `with_none` des modes CLI, soit lever une erreur claire.

### AUDIT-15 — `ValueError` sur saisie de chiffre Unicode
- **Fichier** : `main.py:72-77, 90-95`
- **Catégorie** : runtime
- **Preuve** : `raw_size.isdigit()` accepte `"²"`, `"³"`, `"٣"`, mais `int("²")` lève `ValueError` non capturée.
- **Reco** : Remplacer `isdigit()` par `isdecimal()` ou `try/except ValueError`.

### AUDIT-16 — Surfaces pygame allouées par frame (halos)
- **Fichier** : `visualization/renderers/heap.py:147`, `renderers/merge.py:312`
- **Catégorie** : perf
- **Preuve** : `pygame.Surface(...)` créée à chaque appel dans `_dessiner_halo`. À 60 FPS × 7 algos × plusieurs couches, allocations massives.
- **Impact** : Pression GC, consommation mémoire qui monte en race longue.
- **Reco** : Cacher les surfaces de halo en attribut d'instance, invalidation sur changement de taille.

### AUDIT-17 — Fonts recréées à chaque frame
- **Fichier** : `visualization/renderers/heap.py:297-300`, `renderers/merge.py:301-303`
- **Catégorie** : perf
- **Preuve** : `pygame.font.SysFont("monospace", taille_police)` dans la méthode de rendu. `SysFont` est coûteux (recherche système).
- **Reco** : Cache en attribut d'instance, invalidation sur changement de taille.

---

## Findings Mineurs

### AUDIT-18 — TOCTOU sur `init_db`
- **Fichier** : `benchmarks/database.py:52`
- **Catégorie** : runtime
- **Preuve** : `Path(db_path).exists()` puis `_connect(db_path)` non atomique. Double import legacy possible en lancements concurrents.
- **Reco** : Vérifier l'absence des tables dans la même transaction au lieu de l'existence du fichier.

### AUDIT-19 — `lastrowid` typé `int | None`
- **Fichier** : `benchmarks/database.py:110, 124`
- **Catégorie** : correction
- **Preuve** : Signature déclarée `-> int`, mais `cursor.lastrowid` peut être `None` selon le type stub.
- **Reco** : `assert cursor.lastrowid is not None` avant retour.

### AUDIT-20 — `executescript` + PRAGMA redondant
- **Fichier** : `benchmarks/database.py:54`
- **Catégorie** : qualité
- **Preuve** : `executescript` émet un COMMIT implicite et le `PRAGMA foreign_keys` est déjà dans `_connect`.
- **Reco** : Supprimer le PRAGMA du `_SCHEMA`, documenter l'usage d'`executescript`.

### AUDIT-21 — `_timestamp` sans timezone
- **Fichier** : `benchmarks/exporter.py:11`
- **Catégorie** : qualité
- **Preuve** : `datetime.now()` (locale) alors que `database.py:115` utilise `datetime.now(timezone.utc)`.
- **Reco** : Harmoniser sur UTC.

### AUDIT-22 — Duplication `run_benchmark` / `run_full_benchmark`
- **Fichier** : `benchmarks/runner.py`
- **Catégorie** : qualité
- **Preuve** : Bloc `comparisons/swaps/on_step/start/fn/elapsed` dupliqué.
- **Reco** : Extraire `_run_single(fn, arr) -> dict`.

### AUDIT-23 — Tests bench dépendent de fixture externe non documentée
- **Fichier** : `tests/test_benchmarks/test_runner.py`
- **Catégorie** : tests
- **Preuve** : Fixture `unsorted` héritée d'un `conftest.py` racine, taille/contenu non garantis localement.
- **Reco** : Créer `tests/test_benchmarks/conftest.py` avec fixture explicite.

### AUDIT-24 — `test_time_is_positive` potentiellement flaky
- **Fichier** : `tests/test_benchmarks/test_runner.py:19-22`
- **Catégorie** : tests
- **Preuve** : Sur des tableaux petits avec `time.perf_counter` à faible résolution, elapsed peut arrondir à 0.0.
- **Reco** : Taille minimale ≥ 100 ou tester `>= 0`.

### AUDIT-25 — `test_import_legacy_json` masque le double import
- **Fichier** : `tests/test_benchmarks/test_database.py:105-122`
- **Catégorie** : tests
- **Preuve** : `init_db` auto-importe, puis `import_legacy_json` réimporte. Assertion `> 0` non discriminante.
- **Reco** : Pré-créer la DB pour isoler l'appel explicite.

### AUDIT-26 — Absence de tests `with_none` sur les algos
- **Fichier** : `tests/test_algorithms/*.py`
- **Catégorie** : tests
- **Preuve** : Aucun test ne couvre le comportement attendu quand un `None` est présent, alors que le preset est exposé dans l'UI.
- **Reco** : Ajouter `pytest.raises(TypeError)` ou couvrir le fix AUDIT-14.

### AUDIT-27 — Absence de tests de non-mutation de l'entrée
- **Fichier** : `tests/test_algorithms/*.py`
- **Catégorie** : tests
- **Preuve** : Aucun test ne vérifie que la liste originale reste intacte après appel d'un tri.
- **Reco** : `original = unsorted[:]; tri(unsorted); assert unsorted == original`.

### AUDIT-28 — `test_already_sorted` comparaison faible
- **Fichier** : `tests/test_algorithms/*.py`
- **Catégorie** : tests
- **Preuve** : Compare avec `already_sorted` au lieu de `sorted(already_sorted)`.
- **Reco** : Harmoniser sur `sorted(...)`.

### AUDIT-29 — `test_stop_flag_interrupts_threads` timing fragile
- **Fichier** : `tests/test_visualization/test_race.py:50-62`
- **Catégorie** : tests
- **Preuve** : `time.sleep(0.05)` pour laisser démarrer les threads.
- **Reco** : `threading.Barrier(8)` pour synchronisation déterministe.

### AUDIT-30 — `benchmark_mode` sans handler global
- **Fichier** : `main.py:141-143`
- **Catégorie** : qualité
- **Preuve** : Exceptions DB/import non capturées → traceback brut.
- **Reco** : `try/except` avec message propre et `sys.exit(1)`.

### AUDIT-31 — `Delta` type sous-spécifié
- **Fichier** : `visualization/history.py:81`
- **Catégorie** : correction
- **Preuve** : `Delta = tuple[int, int, str]` mais `add_set` ajoute un 4-tuple. Fonctionne à l'exécution grâce à `len(step)`.
- **Reco** : Union type ou deux types distincts `SwapDelta` / `SetDelta`.

### AUDIT-32 — `ESC` / `QUIT` dans main_menu appellent `sys.exit(0)`
- **Fichier** : `visualization/main_menu.py:903-906, 993-995`
- **Catégorie** : UX
- **Preuve** : Terminaison agressive, bypass du retour normal vers `main.py`.
- **Reco** : Retourner une sentinelle et laisser main.py nettoyer.

---

## Findings Cosmétiques

### AUDIT-33 — Imports/variables inutilisés (ruff)
- **Fichier** : `benchmarks/exporter.py:5` (F401 `pathlib.Path`), `tests/test_benchmarks/test_database.py:3` (F401 `tempfile`) et `:117` (F841 `sid`).
- **Reco** : `ruff --fix`.

### AUDIT-34 — Mypy variables locales mal typées
- **Fichier** : `visualization/datasets.py:109` (`arr` redef), `:132` (`__setitem__ None` dans `list[int]`), `visualization/main_menu.py:609` (`tuple[int, ...]` vs `tuple[int, int, int]`).
- **Catégorie** : qualité
- **Reco** : Typer précisément ou cast explicite, fait en passant lors des fixes liés.

### AUDIT-35 — Import inutile détecté par vulture
- **Fichier** : `tests/test_benchmarks/test_database.py:3`
- **Reco** : Couvert par AUDIT-33.

---

## Zones jugées saines

- Tous les algorithmes de tri (`algorithms/*.py`) : revue manuelle OK, correction et stabilité conformes aux annonces, pas de cas limite cassé.
- `sorting.py` : registre simple, pas de logique à auditer.
- Deps projet : 0 CVE sur `requirements.txt`.
- `pip-audit` sur les deps système (via `--system-site-packages`) a remonté 44 CVE mais elles concernent des paquets système (cryptography, jinja2, urllib3, etc.) non utilisés par le projet. **Hors périmètre.**

## Recommandations transverses

- **Context manager DB** : créer `benchmarks/db_helpers.py::db()` utilisé par tout le module `benchmarks`.
- **Init audio partagé** : extraire `_init_audio()` appelé par `run` et `run_race`.
- **Snapshot atomique des états race** : pattern `states[algo] = new_snapshot_dict` plutôt que mutations successives.
- **Cache surfaces/fonts dans les renderers** : attributs d'instance avec invalidation sur resize.

## Verrou Phase 2

Ce rapport est le livrable Phase 1. Aucune task taskmaster n'est créée tant que l'utilisateur n'a pas validé la liste des findings retenus (Phase 2 bloquée).
