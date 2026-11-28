pipeline {
    agent any

    options {
        skipDefaultCheckout()
        disableConcurrentBuilds()
        timeout(time: 40, unit: 'MINUTES')
    }

    environment {
        IMAGE = 'electronic-library-pr4'
        CONTAINER = 'electronic-library-pr4'
    }

    stages {
        stage('Checkout') {
            steps {
                checkout scm
                sh 'git log -1 --oneline'
            }
        }

        stage('Build image') {
            steps {
                sh '''
                    docker build --platform linux/arm64 --label "org.opencontainers.image.revision=$(git rev-parse HEAD)" -t "$IMAGE:$BUILD_NUMBER" .
                    docker image inspect --format '{{.Os}}/{{.Architecture}}' "$IMAGE:$BUILD_NUMBER"
                '''
            }
        }

        stage('Run container') {
            steps {
                withCredentials([string(credentialsId: 'library-pr4-secret', variable: 'SECRET_KEY')]) {
                    sh '''
                        set -eu
                        if docker container inspect "$CONTAINER" >/dev/null 2>&1; then
                            docker stop "$CONTAINER"
                            docker rm "$CONTAINER"
                        fi
                        docker run -d --name "$CONTAINER" --restart unless-stopped \\
                            -p 127.0.0.1:8004:8000 --env SECRET_KEY \\
                            --mount type=volume,source=library-pr4-data,target=/data "$IMAGE:$BUILD_NUMBER"
                    '''
                }
            }
        }

        stage('Check HTTP') {
            steps {
                sh '''
                    set -eu
                    for attempt in 1 2 3 4 5 6 7 8 9 10; do
                        if curl -fsS --max-time 3 http://127.0.0.1:8004/ | grep -Fq 'Список книг'; then
                            echo "Library is ready: http://127.0.0.1:8004/"
                            exit 0
                        fi
                        sleep 2
                    done
                    docker logs --tail 30 "$CONTAINER"
                    exit 1
                '''
            }
        }

        stage('Deploy to Ubuntu with Ansible') {
            steps {
                sh '''
                    set -eu
                    image="$IMAGE:$BUILD_NUMBER"
                    revision=$(git rev-parse HEAD)
                    archive=$(mktemp "${TMPDIR:-/tmp}/library-pr5.XXXXXX")
                    trap 'rm -f "$archive"' EXIT
                    docker image save --output "$archive" "$image"
                    ansible-playbook -i ansible/inventory.ini ansible/deploy-image.yml \\
                        -e "image_ref=$image" -e "git_revision=$revision" \\
                        -e "image_archive='$archive'"
                '''
            }
        }
    }
}