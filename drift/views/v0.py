from flask import Blueprint, jsonify, request, current_app
from http import HTTPStatus
import logging
import json
import base64

from drift import config, info_parser, metrics
from drift.constants import FACT_NAMESPACE, MOCK_FACT_NAMESPACE
from drift.exceptions import HTTPError, SystemNotReturned
from drift.inventory_service_interface import fetch_systems, get_key_from_headers


section = Blueprint('v0', __name__)


@metrics.comparison_report_requests.time()
@metrics.api_exceptions.count_exceptions()
def comparison_report():
    system_ids = request.args.getlist('system_ids[]')
    auth_key = get_key_from_headers(request.headers)

    fact_namespace = FACT_NAMESPACE
    if config.return_mock_data:
        fact_namespace = MOCK_FACT_NAMESPACE

    try:
        comparisons = info_parser.build_comparisons(fetch_systems(system_ids, auth_key,
                                                                  current_app.logger),
                                                    fact_namespace)
        return jsonify(comparisons)
    except SystemNotReturned as error:
        raise HTTPError(HTTPStatus.BAD_REQUEST, message=error.message)


@section.before_app_request
def ensure_account_number():
    auth_key = get_key_from_headers(request.headers)
    if auth_key:
        identity = json.loads(base64.b64decode(auth_key))['identity']
        if 'account_number' not in identity:
            current_app.logger.debug("account number not found on identity token %s" % auth_key)
            raise HTTPError(HTTPStatus.BAD_REQUEST,
                            message="account number not found on identity token")


@section.before_app_request
def log_username():
    if current_app.logger.level == logging.DEBUG:
        auth_key = get_key_from_headers(request.headers)
        if auth_key:
            identity = json.loads(base64.b64decode(auth_key))['identity']
            current_app.logger.debug("username from identity header: %s" %
                                     identity['user']['username'])
        else:
            current_app.logger.debug("identity header not sent for request")
