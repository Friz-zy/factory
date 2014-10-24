if [ ! -d "env" ]; then
  virtualenv 'env'
fi

rm -rf build/ dist/ Factory.egg-info/
export VIRTUAL_ENV="env"
export PATH="$VIRTUAL_ENV/bin:$PATH"
unset PYTHON_HOME
source env/bin/activate
export PYTHONPATH=.
python setup.py install
cd tests; py.test -v
yes | pip uninstall factory
deactivate
cd ..
rm -rf build/ dist/ Factory.egg-info/

