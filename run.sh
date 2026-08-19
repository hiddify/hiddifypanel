source /opt/hiddify-manager/scripts/common/utils.sh
activate_python_venv
while true; do
    FLASK_RUN_HOST=0.0.0.0 FLASK_RUN_PORT=9000 hiddify-panel-cli run
done
