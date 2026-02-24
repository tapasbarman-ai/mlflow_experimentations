pipeline {
    parameters {
        booleanParam(name: 'FORCE_TRAIN', defaultValue: true, description: 'Force model retraining (First Run)')
    }

    // Stabilized Agent Definition
    agent {
        dockerfile {
            filename 'deployments/jenkins/Dockerfile.ml-agent'
            // Simplified args for better workspace mapping
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
        stage('1. Pre-Flight & Workspace Setup') {
            steps {
                script {
                    echo "--- UNIFIED MLOPS + DEVSECOPS PIPELINE V3.0 ---"
                    sh 'git config --global --add safe.directory "*"'
                    sh 'ls -la'
                    // Ensure a fresh tracking database for high integrity
                    sh 'rm -f mlflow.db || true'
                }
            }
        }

        stage('2. Security Scanning (SAST)') {
            parallel {
                stage('Secrets Detection') {
                    steps {
                        sh 'docker run --rm -v ${WORKSPACE}:/src -w /src zricethezav/gitleaks:latest detect --source . --verbose --redact || true'
                    }
                }
                stage('Code Quality Scan') {
                    steps {
                        sh 'docker run --rm -v ${WORKSPACE}:/src -w /src returntocorp/semgrep semgrep scan --config auto || true'
                    }
                }
            }
        }

        stage('3. SCA (Dependency Check)') {
            steps {
                dependencyCheck additionalArguments: "--format HTML --format JSON --format XML", odcInstallation: 'DP-Check'
                dependencyCheckPublisher pattern: 'dependency-check-report.xml'
            }
        }

        stage('4. Data Validation') {
            steps {
                script {
                    echo "MLOPS: Pulling Data & Validating..."
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
                    echo "MLOPS: Training Model & Logging to MLflow..."
                    sh 'python3 src/pipeline.py'
                }
            }
        }

        stage('6. Static Analysis (SonarQube)') {
            steps {
                script {
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
        }

        stage('7. Governance & Promotion') {
            steps {
                script {
                    echo "MLOPS: Promoting Model to Staging..."
                    sh 'python3 src/promote_model.py --stage Staging'
                    archiveArtifacts artifacts: 'artifacts/**/*', allowEmptyArchive: true
                }
            }
        }

        stage('8. Build & Compliance Audit') {
            steps {
                script {
                    echo "MLOPS: Building Container & Auditing Logs..."
                    sh "docker build -t ${DOCKER_IMAGE}:${BUILD_NUMBER} -f deployments/docker/Dockerfile ."
                    
                    sh "docker run -d --name audit-${BUILD_NUMBER} --network devsecops-network ${DOCKER_IMAGE}:${BUILD_NUMBER}"
                    sleep 15
                    sh "curl -s -X POST http://audit-${BUILD_NUMBER}:8000/predict -d '{\"hr\":10, \"workingday\":1}' -H \"Content-Type: application/json\""
                    sh "docker logs audit-${BUILD_NUMBER}"
                    sh "docker stop audit-${BUILD_NUMBER} && docker rm audit-${BUILD_NUMBER}"
                }
            }
        }

        stage('9. Image Security (Trivy)') {
            steps {
                sh "docker run --rm -v /var/run/docker.sock:/var/run/docker.sock aquasec/trivy image --severity HIGH,CRITICAL ${DOCKER_IMAGE}:${BUILD_NUMBER}"
            }
        }

        stage('10. Release & Production') {
            steps {
                script {
                    withCredentials([usernamePassword(credentialsId: "${NEXUS_CREDENTIALS_ID}", usernameVariable: 'USER', passwordVariable: 'PASS')]) {
                        sh "echo \$PASS | docker login -u \$USER --password-stdin ${NEXUS_REGISTRY}"
                        sh "docker push ${DOCKER_IMAGE}:${BUILD_NUMBER}"
                        sh "docker push ${DOCKER_IMAGE}:latest"
                    }
                    echo "MLOPS: Promoting to PRODUCTION..."
                    sh 'python3 src/promote_model.py --stage Production'
                }
            }
        }

        stage('11. DAST (OWASP ZAP)') {
            steps {
                sh "docker run --rm -t owasp/zap2docker-stable zap-baseline.py -t http://${SONAR_HOST}:9000 -r zap-report.html || true"
            }
        }
    }

    post {
        always {
            script {
                echo "Pipeline Finished. Attempting to archive security reports..."
                // Wrapping in try-catch to prevent pipeline failure if workspace is lost
                try {
                    archiveArtifacts artifacts: '*.json, *.html', allowEmptyArchive: true
                } catch (Exception e) {
                    echo "Could not archive reports: ${e.message}"
                }
            }
        }
    }
}
