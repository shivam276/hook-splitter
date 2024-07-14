import os
from flask import Flask, render_template, request, jsonify, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
import uuid
import requests
import json
from datetime import datetime

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get("POSTGRES_URL")
app.config['SECRET_KEY'] = os.environ.get("SECRET_KEY")  # Add this line
db = SQLAlchemy(app)

class Webhook(db.Model):
    id = db.Column(db.String(36), primary_key=True)
    targets = db.Column(db.Text)  # Comma-separated list of target URLs

class ForwardedWebhook(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    webhook_id = db.Column(db.String(36), db.ForeignKey('webhook.id'), nullable=False)
    timestamp = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    payload = db.Column(db.Text, nullable=False)
    headers = db.Column(db.Text, nullable=False)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/create_webhook', methods=['POST'])
def create_webhook():
    webhook_id = str(uuid.uuid4())
    new_webhook = Webhook(id=webhook_id, targets='')
    db.session.add(new_webhook)
    db.session.commit()
    return redirect(url_for('webhook_page', webhook_id=webhook_id))

@app.route('/webhook/<webhook_id>')
def webhook_page(webhook_id):
    webhook = Webhook.query.get_or_404(webhook_id)
    forwarded_webhooks = ForwardedWebhook.query.filter_by(webhook_id=webhook_id).order_by(ForwardedWebhook.timestamp.desc()).limit(10).all()
    return render_template('webhook_page.html', webhook=webhook, forwarded_webhooks=forwarded_webhooks)

@app.route('/add_target/<webhook_id>', methods=['POST'])
def add_target(webhook_id):
    webhook = Webhook.query.get_or_404(webhook_id)
    new_target = request.form['target']

    # Check if the new target is the same as the host URL
    host_url = url_for('receive_webhook', webhook_id=webhook_id, _external=True)
    if new_target == host_url:
        flash('Error: Cannot add the host URL as a target.', 'error')
        return redirect(url_for('webhook_page', webhook_id=webhook_id))
    webhook_targets = webhook.targets.split(',')
    if webhook.targets:
        if new_target.strip() in webhook_targets:
            flash('Error: Target URL already exists.', 'error')
            return redirect(url_for('webhook_page', webhook_id=webhook_id))
        webhook.targets += f',{new_target.strip()}'
    else:
        webhook.targets = new_target.strip()
    db.session.commit()
    flash('Target URL added successfully.', 'success')
    return redirect(url_for('webhook_page', webhook_id=webhook_id))

@app.route('/remove_target/<webhook_id>', methods=['POST'])
def remove_target(webhook_id):
    webhook = Webhook.query.get_or_404(webhook_id)
    target_to_remove = request.form['target']
    targets = webhook.targets.split(',')
    targets.remove(target_to_remove)
    webhook.targets = ','.join(targets)
    db.session.commit()
    flash('Target URL removed successfully.', 'success')
    return redirect(url_for('webhook_page', webhook_id=webhook_id))

@app.route('/webhook/<webhook_id>/receive', methods=['POST', 'GET'])
def receive_webhook(webhook_id):
    webhook = Webhook.query.get(webhook_id)
    if not webhook:
        return jsonify({'error': 'Webhook not found'}), 404

    if request.method == 'GET':
        # For GET requests, forward to the first target and return its response
        targets = webhook.targets.split(',')
        if targets and targets[0]:
            try:
                response = requests.get(targets[0], params=request.args)
                return response.content, response.status_code, response.headers.items()
            except requests.RequestException as e:
                return jsonify({'error': f'Error forwarding GET request: {str(e)}'}), 500
        else:
            return jsonify({'error': 'No targets configured'}), 400

    # For POST requests, continue with the existing logic
    payload = request.json
    headers = {key: value for key, value in request.headers if key.lower().startswith('x-')}

    forwarded_webhook = ForwardedWebhook(
        webhook_id=webhook_id,
        payload=json.dumps(payload),  # Serialize to JSON string
        headers=json.dumps(headers)  # Serialize to JSON string
    )

    db.session.add(forwarded_webhook)
    db.session.commit()

    for target in webhook.targets.split(','):
        if target:
            try:
                requests.post(target, json=payload, headers=headers)
            except requests.RequestException as e:
                print(f"Error forwarding to {target}: {str(e)}")

    return jsonify({'status': 'ok'}), 200

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run()
