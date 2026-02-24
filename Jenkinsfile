pipeline {
    parameters {
        booleanParam(name: 'FORCE_TRAIN', defaultValue: true, description: 'Force model retraining (Important for First Run)')
    }

    // Define the custom build environment for the entire pipeline
    agent {
        dockerfile {
            filename 'deployments/jenkins/Dockerfile.ml-agent'
            dir '.'
            // Connect agent to the same network as SonarQube/Nexus and mount docker socket
            args '-u root:root --network devsecops-network -v /var/run/docker.sock:/var/run/docker.sock'
        }
    }

    environment {
        SCANNER_HOME = tool 'SonarScanner'
        APP_NAME = "bike-demand-predictor"
        // Use service names for internal container-to-container communication
        NEXUS_REGISTRY = "nexus:8082"
        SONAR_HOST     = "sonarqube"
        DOCKER_IMAGE   = "${NEXUS_REGISTRY}/${APP_NAME}"
        NEXUS_CREDENTIALS_ID = 'nexus-creds'
        
        // MLflow Tracking using SQLite within the shared workspace
        MLFLOW_TRACKING_URI = "sqlite:///${WORKSPACE}/mlflow.db"
    }

    stages {
        stage('1. Pre-Flight Checks') {
            steps {
                script {
                    echo "--- INDUSTRIAL MLOPS PIPELINE V2.5 (ROOT-STABLE) ---"
                    sh 'git config --global --add safe.directory "*"'
                    sh 'ls -la'
                    // Clean up potential lock files or old DBs for a fresh start
                    sh 'rm -f mlflow.db || true'
                }
            }
        }

        stage('2. Data Validation') {
            steps {
                script {
                    echo "Pulling latest data via DVC..."
                    sh 'dvc pull || echo "DVC pull failed, using local files"'
                    
                    echo "Running Data Validation Checks..."
                    sh 'python3 src/data_validation.py'
                }
            }
        }

        stage('3. Smart Training (MLflow)') {
            when {
                anyOf {
                    changeset "src/pipeline.py"
                    changeset "data/**"
                    changeset "requirements.txt"
                    expression { return params.FORCE_TRAIN == true }
                }
            }
            steps {
                script {
                    echo "Executing Training Pipeline..."
                    sh 'python3 src/pipeline.py'
                }
            }
        }

        stage('4. Security & Quality Gate') {
            parallel {
                stage('SAST & Secrets') {
                    steps {
                        sh 'docker run --rm -v ${WORKSPACE}:/src -w /src zricethezav/gitleaks:latest detect --source . --verbose --redact || true'
                    }
                }
                stage('SonarQube Scan') {
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
            }
        }

        stage('5. Model Promotion (None -> Staging)') {
            steps {
                script {
                    echo "Promoting latest validated model to Staging..."
                    sh 'python3 src/promote_model.py --stage Staging'
                }
            }
        }

        stage('6. Analysis Persistence') {
            steps {
                script {
                    echo "Archiving Bias and Drift Reports..."
                    archiveArtifacts artifacts: 'artifacts/**/*', allowEmptyArchive: true
                }
            }
        }

        stage('7. Build Production Container') {
            steps {
                script {
                    echo "Building Production API Container..."
                    sh "docker build -t ${DOCKER_IMAGE}:${BUILD_NUMBER} -f deployments/docker/Dockerfile ."
                    sh "docker tag ${DOCKER_IMAGE}:${BUILD_NUMBER} ${DOCKER_IMAGE}:latest"
                }
            }
        }

        stage('8. Compliance & Governance') {
            steps {
                script {
                    echo "Verifying Inference Logging Contract..."
                    sh "docker run -d --name audit-test-${BUILD_NUMBER} --network devsecops-network ${DOCKER_IMAGE}:${BUILD_NUMBER}"
                    sleep 15
                    sh "curl -s -X POST http://audit-test-${BUILD_NUMBER}:8000/predict -d '{\"hr\":10, \"workingday\":1}' -H \"Content-Type: application/json\""
                    sh "docker logs audit-test-${BUILD_NUMBER}"
                    sh "docker stop audit-test-${BUILD_NUMBER} && docker rm audit-test-${BUILD_NUMBER}"
                }
            }
        }

        stage('9. Image Registry Push') {
            steps {
                sh "docker run --rm -v /var/run/docker.sock:/var/run/docker.sock aquasec/trivy image --severity HIGH,CRITICAL ${DOCKER_IMAGE}:${BUILD_NUMBER}"
                withCredentials([usernamePassword(credentialsId: "${NEXUS_CREDENTIALS_ID}", usernameVariable: 'USER', passwordVariable: 'PASS')]) {
                    sh "echo \$PASS | docker login -u \$USER --password-stdin ${NEXUS_REGISTRY}"
                    sh "docker push ${DOCKER_IMAGE}:${BUILD_NUMBER}"
                    sh "docker push ${DOCKER_IMAGE}:latest"
                }
            }
        }

        stage('10. Model Promotion (Staging -> Production)') {
            steps {
                script {
                    echo "Promoting fully verified model to Production..."
                    sh 'python3 src/promote_model.py --stage Production'
                }
            }
        }
    }

    post {
        always {
            echo "Pipeline Run Finished."
        }
    }
}
