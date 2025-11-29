#pragma once

#include <QObject>
#include <QThread>
#include <QTimer>
#include <QString>

class GestureWorker;

class GestureEngine : public QObject
{
    Q_OBJECT

public:
    explicit GestureEngine(QObject *parent = nullptr);
    ~GestureEngine();

    void start();
    void stop();

signals:
    void gestureDetected(const QString &gestureName);

private:
    QThread workerThread_;
    GestureWorker *worker_ = nullptr;
};
