# Diabetes Prediction System

An intelligent healthcare platform for early diabetes detection and patient management using machine learning. The system provides end-to-end healthcare workflow management including patient registration, health record tracking, diabetes risk prediction, prescription management, lab test integration, and pharmacy services.

## 📋 Table of Contents

- [Overview](#overview)
- [Features](#features)
- [Technology Stack](#technology-stack)
- [System Architecture](#system-architecture)
- [Installation](#installation)
- [Configuration](#configuration)
- [Running the Application](#running-the-application)
- [API Documentation](#api-documentation)
- [Testing](#testing)
- [Security and Operations](#security-and-operations)
- [Project Structure](#project-structure)
- [Deployment](#deployment)
- [Contributing](#contributing)
- [License](#license)

## 🎯 Overview

The Diabetes Prediction System is a comprehensive healthcare management platform that leverages machine learning to predict diabetes risk based on patient health data. The system supports multiple user roles including patients, doctors, nurses, lab technicians, pharmacists, and administrators, creating a complete healthcare ecosystem.

### Key Features

- **AI-Powered Prediction**: Machine learning model (Logistic Regression, Random Forest, XGBoost) for diabetes risk assessment
- **Multi-Role System**: Support for patients, doctors, nurses, lab technicians, pharmacists, and administrators
- **Health Records Management**: Track patient health metrics over time
- **Prescription Management**: Digital prescription creation and dispensing
- **Lab Test Integration**: Order and manage lab tests with result entry and validation
- **Appointment Scheduling**: Book and manage patient appointments
- **Payment Processing**: Integrated payment system with Ethiopian Birr support
- **Audit Logging**: Complete audit trail of all system actions
- **Security Features**: Password policies, rate limiting, CSRF protection, input sanitization

## 🛠️ Technology Stack

### Backend
- **Python 3.11+**
- **Flask 2.3+** - Web framework
- **SQLAlchemy 2.0+** - ORM
- **SQLite/PostgreSQL** - Database
- **JWT** - Authentication
- **scikit-learn** - Machine learning
- **pandas/numpy** - Data processing

### Frontend
- **HTML5/CSS3** - Structure and styling
- **JavaScript (ES6+)** - Client-side logic
- **Tailwind CSS** - Responsive design
- **Bootstrap Icons** - Icon library
- **Chart.js** - Data visualization

### Development Tools
- **Flask-Migrate** - Database migrations
- **pytest** - Testing framework
- **Flask-CORS** - Cross-origin resource sharing
- **python-dotenv** - Environment variables

## 🏗️ System Architecture

## 🔐 Security and Operations

- Security policy: `SECURITY.md`
- Operations runbook: `docs/OPERATIONS_RUNBOOK.md`
- Compliance checklist: `docs/COMPLIANCE_CHECKLIST.md`
- Model governance: `docs/MODEL_GOVERNANCE.md`
- Migration integrity check: `tools/check_migrations.py`
- Backup/restore smoke check: `tools/backup_restore_smoke.py`
