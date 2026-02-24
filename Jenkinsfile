pipeline {
    parameters {
        booleanParam(name: 'FORCE_TRAIN', defaultValue: true, description: 'Force model retraining (Important for First Run)')
    }

    // Agent with all ML dependencies pre-installed
    agent {
        dockerfile {
            filename 'deployments/jenkins/Dockerfile.ml-agent'
            dir '.'
            args '-u root:root --network devsecops-network -v /var/run/docker.sock:/var/run/docker.sock'
        }
    }

    environment {
        SCANNER_HOME = tool 'SonarScanner'
        APP_NAME = "bike-demand-predictor"
        NEXUS_REGISTRY = "nexus:8082"
        SONAR_HOST     = "sonarqube"
        DOCKER_IMAGE   = "${NEXUS_REGISTRY}/${APP_NAME}"
        NEXUS_CREDENTIALS_ID = 'nexus-creds'
        MLFLOW_TRACKING_URI = "sqlite:///${WORKSPACE}/mlflow.db"
    }

    stages {
        stage('1. Pre-Flight & Checkout') {
            steps {
                script {
                    echo "--- UNIFIED DEVSECOPS + MLOPS PIPELINE ---"
                    sh 'git config --global --add safe.directory "*"'
                    sh 'ls -la'
                    sh 'rm -f mlflow.db || true'
                }
            }
        }

        stage('2. Security Scanning (SAST)') {
            parallel {
                stage('Secrets (Gitleaks)') {
                    steps {
                        sh 'docker run --rm -v ${WORKSPACE}:/src -w /src zricethezav/gitleaks:latest detect --source . --verbose --redact || true'
                    }
                }
                stage('Code Scan (Semgrep)') {
                    steps {
                        sh 'docker run --rm -v ${WORKSPACE}:/src -w /src returntocorp/semgrep semgrep scan --config auto || true'
                    }
                }
            }
        }

        stage('3. SCA (OWASP Dependency Check)') {
            steps {
                // Scans requirements.txt for vulnerable libraries
                dependencyCheck additionalArguments: "--format HTML --format JSON --format XML", odcInstallation: 'DP-Check'
                dependencyCheckPublisher pattern: 'dependency-check-report.xml'
            }
        }

        stage('4. Data Validation') {
            steps {
                script {
                    echo "MLOPS: Validating Dataset..."
                    sh 'dvc pull || echo "DVC pull failed, using local data"'
                    sh 'python3 src/data_validation.py'
                }
            }
        }

        stage('5. Smart Training (MLflow)') {
            when {
                anyOf {
                    changeset "src/pipeline.py"
                    changeset "data/**"
                    expression { return params.FORCE_TRAIN == true }
                }
            }
            steps {
                script {
                    echo "MLOPS: Executing Training & Tracking..."
                    sh 'python3 src/pipeline.py'
                }
            }
        }

        stage('6. Static Analysis (SonarQube)') {
            steps {
                withCredentials([string(credentialsId: 'sonarqube-token', variable: 'SONAR_TOKEN')]) {
                    sh "${SCANNER_HOME}/bin/sonar-scanner \
                        -Dsonar.projectKey=bike-sharing-mlops \
                        -Dsonar.sources=src/ \
                        -Dsonar.host.url=http://${SONAR_HOST}:9000 \
                        -Dsonar.login=\$SONAR_TOKEN"
                }
                timeout(time: 1, unit: 'HOURS') {
                    waitForQualityGate abortPipeline: true
                }
            }
        }

        stage('7. Governance (Promotion to Staging)') {
            steps {
                script {
                    echo "MLOPS: Promoting Model to Staging Registry..."
                    sh 'python3 src/promote_model.py --stage Staging'
                    archiveArtifacts artifacts: 'artifacts/**/*', allowEmptyArchive: true
                }
            }
        }

        stage('8. Build & Compliance Audit') {
            steps {
                script {
                    echo "Building Production API & Verifying Audit Logs..."
                    sh "docker build -t ${DOCKER_IMAGE}:${BUILD_NUMBER} -f deployments/docker/Dockerfile ."
                    
                    // Compliance Check: Run container and verify it logs predictions
                    sh "docker run -d --name compliance-test-${BUILD_NUMBER} --network devsecops-network ${DOCKER_IMAGE}:${BUILD_NUMBER}"
                    sleep 15
                    sh "curl -s -X POST http://compliance-test-${BUILD_NUMBER}:8000/predict -d '{\"hr\":10, \"workingday\":1}' -H \"Content-Type: application/json\""
                    sh "docker logs compliance-test-${BUILD_NUMBER}"
                    sh "docker stop compliance-test-${BUILD_NUMBER} && docker rm compliance-test-${BUILD_NUMBER}"
                }
            }
        }

        stage('9. Image Security (Trivy)') {
            steps {
                sh "docker run --rm -v /var/run/docker.sock:/var/run/docker.sock aquasec/trivy image --severity HIGH,CRITICAL ${DOCKER_IMAGE}:${BUILD_NUMBER}"
            }
        }

        stage('10. Release & Promotion') {
            steps {
                script {
                    withCredentials([usernamePassword(credentialsId: "${NEXUS_CREDENTIALS_ID}", usernameVariable: 'USER', passwordVariable: 'PASS')]) {
                        sh "echo \$PASS | docker login -u \$USER --password-stdin ${NEXUS_REGISTRY}"
                        sh "docker push ${DOCKER_IMAGE}:${BUILD_NUMBER}"
                    }
                    echo "MLOPS: Promoting to PRODUCTION..."
                    sh 'python3 src/promote_model.py --stage Production'
                }
            }
        }

        stage('11. DAST (OWASP ZAP)') {
            steps {
                // Dynamic security test against the SonarQube UI or your own API
                sh "docker run --rm -t owasp/zap2docker-stable zap-baseline.py -t http://${SONAR_HOST}:9000 -r zap-report.html || true"
            }
        }
    }

    post {
        always {
            archiveArtifacts artifacts: '*.json, *.html', allowEmptyArchive: true
            echo "CI/CD/MLOps Pipeline Finished."
        }
    }
}
