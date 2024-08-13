import logging

import os
import sys
import subprocess
import json
import shutil

from pathlib import Path
from datetime import datetime
from typing import List

from eodata.__about__ import __version__

logger = logging.getLogger()

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO,
)


def build_artifact() -> str:
    if sys.platform == 'darwin':
        extension = 'app'
    elif sys.platform == 'win32':
        extension = 'exe'
    else:
        extension = 'bin'
    return f'build/eodata.{extension}'


def clean() -> None:
    logger.info('Cleaning build folder...')
    build = Path('build')
    if build.exists():
        shutil.rmtree(build)


def run_nuitka(*build_parameters: str) -> None:
    logger.info('Running nuitka build...')
    subprocess.run(
        [
            sys.executable,
            '-m',
            'nuitka',
            '--enable-plugin=pyside6',
            '--file-description=Endless Data Studio',
            '--product-name=Endless Data Studio',
            f'--product-version={__version__}',
            f'--copyright=Copyright © {datetime.now().year} Jonah Jeleniewski',
            '--main=eodata.py',
            '--assume-yes-for-downloads',
            '--output-dir=build',
            *build_parameters,
        ],
        check=True,
    )


def notarize() -> None:
    app_bundle = build_artifact()
    app_bundle_zip = f'{app_bundle}.zip'

    logger.info('Checking codesigning is valid...')
    subprocess.run(
        ['/usr/bin/codesign', '--verify', '--deep', '--strict', '--verbose=2', app_bundle],
        check=True,
    )

    logger.info('Zipping the app bundle...')
    subprocess.run(
        [
            '/usr/bin/ditto',
            '-c',
            '-k',
            '--sequesterRsrc',
            '--keepParent',
            app_bundle,
            app_bundle_zip,
        ],
        capture_output=True,
        text=True,
        check=True,
    )

    result = subprocess.run(
        [
            'xcrun',
            'notarytool',
            'submit',
            app_bundle_zip,
            *authorization_args(),
            '--wait',
            '--output-format',
            'json',
        ],
        capture_output=True,
        text=True,
        check=True,
    )
    json_response = json.loads(result.stdout.strip())

    log_output = None
    if isinstance(json_response.get('id'), str):
        log_output = get_notarization_logs(json_response['id'])

    if json_response.get('status') != 'Accepted':
        message = f"Notarization failed\n\n{result.stdout}"
        if log_output:
            message += f"\n\nDiagnostics from notarytool log: {log_output}"
        raise Exception(message)

    logger.info('Stapling the app bundle...')
    subprocess.run(['xcrun', 'stapler', 'staple', app_bundle], check=True)

    logger.info('Notarization successful 🎉')


def get_notarization_logs(id: str) -> str:
    return subprocess.run(
        ['xcrun', 'notarytool', 'log', *authorization_args(), id], capture_output=True, text=True
    ).stdout


def authorization_args() -> List[str]:
    return [
        '--apple-id',
        os.getenv('APPLE_ID'),
        '--team-id',
        os.getenv('APPLE_TEAM_ID'),
        '--password',
        os.getenv('APPLE_APP_SPECIFIC_PASSWORD'),
    ]


def create_dmg(output_name: str) -> None:
    logger.info('Creating disk image file...')

    app_bundle = 'build/Endless Data Studio.app'
    os.rename(build_artifact(), app_bundle)

    subprocess.run(
        [
            "hdiutil",
            "create",
            "-volname",
            "Endless Data Studio",
            "-srcfolder",
            app_bundle,
            "-ov",
            "-format",
            "UDZO",
            f'build/{output_name}',
        ],
        check=True,
    )

    shutil.rmtree(app_bundle)


def main() -> None:
    clean()

    if sys.platform == 'darwin':
        for arch in ['arm64', 'x86_64']:
            logger.info(f'Running {arch} macos build...')
            run_nuitka(
                '--macos-create-app-bundle',
                '--macos-app-name=Endless Data Studio',
                '--macos-signed-app-name=dev.cirras.eodata',
                '--macos-app-icon=./icons/icon.icns',
                '--macos-app-protected-resource='
                + 'LSApplicationCategoryType:public.app-category.developer-tools',
                '--macos-sign-identity=auto',
                '--macos-sign-notarization',
                f'--macos-app-version={__version__}',
                f'--macos-target-arch={arch}',
            )
            notarize()
            create_dmg(f'eodata-{__version__}-{arch}.dmg')
    else:
        if sys.platform == 'win32':
            run_nuitka(
                '--mingw',
                '--onefile',
                '--windows-console-mode=disable',
                '--windows-icon-from-ico=./icons/icon.ico',
            )
        else:
            run_nuitka('--onefile')

        artifact = Path(build_artifact())
        artifact.rename(artifact.with_name(f'eodata-{__version__}{artifact.suffix}'))


if __name__ == '__main__':
    main()
