"""
MinerUtoMD 安装配置
"""
from setuptools import setup

with open('README.md', 'r', encoding='utf-8') as f:
    long_description = f.read()

setup(
    name='minerutomd',
    version='1.0.0',
    author='DuMate',
    description='文档转换工作流工具 - PDF/Word到Markdown及多格式转换',
    long_description=long_description,
    long_description_content_type='text/markdown',
    url='https://github.com/dumate/minerutomd',
    py_modules=[
        'main',
        'doc_workflow',
        'mineru_extractor',
        'pandoc_converter',
        'markdown_optimizer',
        'watermark_remover',
        'environment_diagnostics',
        'quality_checker',
        'task_manifest',
        'gui',
        'gui_simple',
    ],
    classifiers=[
        'Development Status :: 4 - Beta',
        'Intended Audience :: Developers',
        'Topic :: Text Processing :: Markup',
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: 3.9',
        'Programming Language :: Python :: 3.10',
        'Programming Language :: Python :: 3.11',
    ],
    python_requires='>=3.8',
    install_requires=[
        'click>=8.1.0',
        'rich>=13.0.0',
        'pyyaml>=6.0',
        'pypandoc>=1.11',
        'python-docx>=0.8.11',
        'markdown>=3.5',
        'beautifulsoup4>=4.12.0',
    ],
    extras_require={
        'full': [
            'magic-pdf[full]>=0.6.0',
        ],
    },
    entry_points={
        'console_scripts': [
            'minerutomd=main:main',
        ],
    },
    include_package_data=True,
    zip_safe=False,
)
