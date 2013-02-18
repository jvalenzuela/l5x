from distutils.core import setup

setup(name='l5x',
      version='0.1',
      author='Jason Valenzuela',
      author_email='jvalenzuela1977@gmail.com',
      packages=['l5x', 'tests'],
      url='http://pypi.python.org/pypi/l5x/',
      license='LICENSE.txt',
      description='RSLogix .L5X interface.',
      long_description=open('README.txt').read())
