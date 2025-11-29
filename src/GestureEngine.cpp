#include "GestureEngine.h"
#include <zmq.h>
#include <QDebug>

class GestureWorker : public QObject
{
    Q_OBJECT
public:
    void run()
    {
        void *context = zmq_ctx_new();
        void *socket = zmq_socket(context, ZMQ_SUB);

        zmq_connect(socket, "tcp://localhost:5555");
        zmq_setsockopt(socket, ZMQ_SUBSCRIBE, "", 0);

        char buffer[64];

        while (running_)
        {
            int size = zmq_recv(socket, buffer, sizeof(buffer), ZMQ_DONTWAIT);
            if (size > 0)
            {
                buffer[size] = '\0';
                emit gestureDetected(QString::fromUtf8(buffer));
            }
            QThread::msleep(5);
        }

        zmq_close(socket);
        zmq_ctx_destroy(context);
    }

    void stop()
    {
        running_ = false;
    }

signals:
    void gestureDetected(const QString &gestureName);

private:
    bool running_ = true;
};

GestureEngine::GestureEngine(QObject *parent)
    : QObject(parent)
{
    worker_ = new GestureWorker();
    worker_->moveToThread(&workerThread_);

    connect(&workerThread_, &QThread::started,
            worker_, &GestureWorker::run);

    connect(worker_, &GestureWorker::gestureDetected,
            this, &GestureEngine::gestureDetected);
}

GestureEngine::~GestureEngine()
{
    stop();
}

void GestureEngine::start()
{
    if (!workerThread_.isRunning())
        workerThread_.start();
}

void GestureEngine::stop()
{
    if (workerThread_.isRunning())
    {
        QMetaObject::invokeMethod(worker_, "stop");
        workerThread_.quit();
        workerThread_.wait();
    }
}

#include "GestureEngine.moc"
