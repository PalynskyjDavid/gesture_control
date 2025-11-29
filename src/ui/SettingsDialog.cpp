#include "SettingsDialog.h"
#include <QVBoxLayout>
#include <QHBoxLayout>
#include <QLabel>
#include <QDoubleSpinBox>
#include <QSpinBox>
#include <QComboBox>
#include <QCheckBox>
#include <QPushButton>
#include <QFile>
#include <QJsonDocument>
#include <QJsonObject>
#include <QJsonValue>
#include <QJsonArray>
#include <QMessageBox>

#include <QStandardPaths>
#include <QDir>

static QString configPath()
{
    // relative to project: python/config.json
    return QDir::current().filePath("python/config.json");
}

SettingsDialog::SettingsDialog(QWidget *parent)
    : QDialog(parent)
{
    setWindowTitle(tr("Gesture Settings"));
    auto *layout = new QVBoxLayout(this);

    // classifier group (simple vertical layout)
    auto *labelC = new QLabel(tr("Classifier thresholds:"), this);
    layout->addWidget(labelC);

    auto *hBox1 = new QHBoxLayout();
    historySpin_ = new QSpinBox();
    historySpin_->setRange(1, 32);
    swipeSpin_ = new QDoubleSpinBox();
    swipeSpin_->setRange(0.0, 10.0);
    swipeSpin_->setDecimals(3);
    zoomSpin_ = new QDoubleSpinBox();
    zoomSpin_->setRange(0.0, 1.0);
    zoomSpin_->setDecimals(3);
    dragSpin_ = new QDoubleSpinBox();
    dragSpin_->setRange(0.0, 1.0);
    dragSpin_->setDecimals(3);

    hBox1->addWidget(new QLabel(tr("history_len:")));
    hBox1->addWidget(historySpin_);
    hBox1->addWidget(new QLabel(tr("swipe_thresh:")));
    hBox1->addWidget(swipeSpin_);
    hBox1->addWidget(new QLabel(tr("zoom_thresh:")));
    hBox1->addWidget(zoomSpin_);
    hBox1->addWidget(new QLabel(tr("drag_thresh:")));
    hBox1->addWidget(dragSpin_);
    layout->addLayout(hBox1);

    auto *hBox1b = new QHBoxLayout();
    pinchSpin_ = new QDoubleSpinBox();
    pinchSpin_->setRange(0.0, 1.0);
    pinchSpin_->setDecimals(4);
    thumbAngleSpin_ = new QDoubleSpinBox();
    thumbAngleSpin_->setRange(0.0, 360.0);
    thumbAngleSpin_->setDecimals(1);
    hBox1b->addWidget(new QLabel(tr("pinch_dist_thresh:")));
    hBox1b->addWidget(pinchSpin_);
    hBox1b->addWidget(new QLabel(tr("thumb_angle_thresh:")));
    hBox1b->addWidget(thumbAngleSpin_);
    layout->addLayout(hBox1b);

    // multi-hand
    auto *labelM = new QLabel(tr("Multi-hand:"), this);
    layout->addWidget(labelM);
    auto *hBox2 = new QHBoxLayout();
    twoHandEnable_ = new QCheckBox(tr("Enable two-hand zoom"), this);
    twoHandWindow_ = new QSpinBox();
    twoHandWindow_->setRange(1, 16);
    twoHandThresh_ = new QDoubleSpinBox();
    twoHandThresh_->setRange(0.0, 1.0);
    twoHandThresh_->setDecimals(3);
    hBox2->addWidget(twoHandEnable_);
    hBox2->addWidget(new QLabel(tr("window:")));
    hBox2->addWidget(twoHandWindow_);
    hBox2->addWidget(new QLabel(tr("thr:")));
    hBox2->addWidget(twoHandThresh_);
    layout->addLayout(hBox2);

    // smoothing
    auto *labelS = new QLabel(tr("Smoothing / confidence:"), this);
    layout->addWidget(labelS);

    auto *hBox3 = new QHBoxLayout();
    smoothingModeCombo_ = new QComboBox();
    smoothingModeCombo_->addItems({"voting", "ema", "hysteresis"});
    emaAlphaSpin_ = new QDoubleSpinBox();
    emaAlphaSpin_->setRange(0.0, 1.0);
    emaAlphaSpin_->setDecimals(3);
    hystEnterSpin_ = new QDoubleSpinBox();
    hystExitSpin_ = new QDoubleSpinBox();
    hystEnterSpin_->setRange(0.0, 1.0);
    hystExitSpin_->setRange(0.0, 1.0);
    hystEnterSpin_->setDecimals(3);
    hystExitSpin_->setDecimals(3);
    hBox3->addWidget(new QLabel(tr("mode:")));
    hBox3->addWidget(smoothingModeCombo_);
    hBox3->addWidget(new QLabel(tr("ema alpha:")));
    hBox3->addWidget(emaAlphaSpin_);
    hBox3->addWidget(new QLabel(tr("hyst enter:")));
    hBox3->addWidget(hystEnterSpin_);
    hBox3->addWidget(new QLabel(tr("hyst exit:")));
    hBox3->addWidget(hystExitSpin_);
    layout->addLayout(hBox3);

    // debug
    auto *labelD = new QLabel(tr("Debug / UI"), this);
    layout->addWidget(labelD);
    auto *hBox4 = new QHBoxLayout();
    drawLandmarks_ = new QCheckBox(tr("Draw landmarks"));
    showFps_ = new QCheckBox(tr("Show FPS"));
    fpsWindowSpin_ = new QSpinBox();
    fpsWindowSpin_->setRange(1, 200);
    hBox4->addWidget(drawLandmarks_);
    hBox4->addWidget(showFps_);
    hBox4->addWidget(new QLabel(tr("fps window:")));
    hBox4->addWidget(fpsWindowSpin_);
    layout->addLayout(hBox4);

    // buttons
    auto *btnBox = new QHBoxLayout();
    applyBtn_ = new QPushButton(tr("Apply"));
    resetBtn_ = new QPushButton(tr("Reset"));
    btnBox->addStretch();
    btnBox->addWidget(resetBtn_);
    btnBox->addWidget(applyBtn_);
    layout->addLayout(btnBox);

    connect(applyBtn_, &QPushButton::clicked, this, &SettingsDialog::onApply);
    connect(resetBtn_, &QPushButton::clicked, this, &SettingsDialog::onReset);

    loadFromConfig();
}

void SettingsDialog::loadFromConfig()
{
    QString path = configPath();
    QFile f(path);
    if (!f.open(QIODevice::ReadOnly))
    {
        // set defaults
        historySpin_->setValue(4);
        swipeSpin_->setValue(1.0);
        zoomSpin_->setValue(0.15);
        dragSpin_->setValue(0.05);
        pinchSpin_->setValue(0.08);
        thumbAngleSpin_->setValue(50.0);

        twoHandEnable_->setChecked(true);
        twoHandWindow_->setValue(4);
        twoHandThresh_->setValue(0.03);

        smoothingModeCombo_->setCurrentText("voting");
        emaAlphaSpin_->setValue(0.4);
        hystEnterSpin_->setValue(0.7);
        hystExitSpin_->setValue(0.4);

        drawLandmarks_->setChecked(true);
        showFps_->setChecked(true);
        fpsWindowSpin_->setValue(20);
        return;
    }

    QByteArray ba = f.readAll();
    f.close();
    QJsonDocument doc = QJsonDocument::fromJson(ba);
    if (!doc.isObject())
        return;
    QJsonObject root = doc.object();

    QJsonObject cls = root["classifier"].toObject();
    historySpin_->setValue(cls["history_len"].toInt(4));
    swipeSpin_->setValue(cls["swipe_speed_thresh"].toDouble(1.0));
    zoomSpin_->setValue(cls["zoom_speed_thresh"].toDouble(0.15));
    dragSpin_->setValue(cls["drag_speed_thresh"].toDouble(0.05));
    pinchSpin_->setValue(cls["pinch_distance_threshold"].toDouble(0.08));
    thumbAngleSpin_->setValue(cls["pinch_thumb_angle_thresh"].toDouble(50.0));

    QJsonObject mh = root["multi_hand"].toObject();
    twoHandEnable_->setChecked(mh["enable_two_hand_zoom"].toBool(true));
    twoHandWindow_->setValue(mh["two_hand_zoom_window"].toInt(4));
    twoHandThresh_->setValue(mh["two_hand_zoom_thresh"].toDouble(0.03));

    QJsonObject dbg = root["debug"].toObject();
    drawLandmarks_->setChecked(dbg["draw_landmarks"].toBool(true));
    showFps_->setChecked(dbg["show_fps"].toBool(true));
    fpsWindowSpin_->setValue(dbg["fps_window"].toInt(20));

    QJsonObject smooth = root["smoothing"].toObject();
    QString mode = smooth["mode"].toString("voting");
    smoothingModeCombo_->setCurrentText(mode);
    emaAlphaSpin_->setValue(smooth["ema_alpha"].toDouble(0.4));
    hystEnterSpin_->setValue(smooth["hysteresis_enter"].toDouble(0.7));
    hystExitSpin_->setValue(smooth["hysteresis_exit"].toDouble(0.4));
}

void SettingsDialog::writeToConfigFile()
{
    // Build JSON
    QJsonObject root;
    QJsonObject classifier;
    classifier["history_len"] = historySpin_->value();
    classifier["swipe_speed_thresh"] = swipeSpin_->value();
    classifier["zoom_speed_thresh"] = zoomSpin_->value();
    classifier["drag_speed_thresh"] = dragSpin_->value();
    classifier["pinch_distance_threshold"] = pinchSpin_->value();
    classifier["pinch_thumb_angle_thresh"] = thumbAngleSpin_->value();
    root["classifier"] = classifier;

    QJsonObject multi;
    multi["enable_two_hand_zoom"] = twoHandEnable_->isChecked();
    multi["two_hand_zoom_window"] = twoHandWindow_->value();
    multi["two_hand_zoom_thresh"] = twoHandThresh_->value();
    root["multi_hand"] = multi;

    QJsonObject debug;
    debug["draw_landmarks"] = drawLandmarks_->isChecked();
    debug["show_fps"] = showFps_->isChecked();
    debug["fps_window"] = fpsWindowSpin_->value();
    root["debug"] = debug;

    QJsonObject smoothing;
    smoothing["mode"] = smoothingModeCombo_->currentText();
    smoothing["ema_alpha"] = emaAlphaSpin_->value();
    smoothing["hysteresis_enter"] = hystEnterSpin_->value();
    smoothing["hysteresis_exit"] = hystExitSpin_->value();
    root["smoothing"] = smoothing;

    // write to file
    QString path = configPath();
    QFile f(path);
    if (!f.open(QIODevice::WriteOnly))
    {
        QMessageBox::warning(this, tr("Write error"),
                             tr("Failed to write config.json to %1").arg(path));
        return;
    }
    QJsonDocument doc(root);
    f.write(doc.toJson());
    f.close();
}

void SettingsDialog::onApply()
{
    writeToConfigFile();
    emit configSaved();
    accept();
}

void SettingsDialog::onReset()
{
    // remove file if exists
    QString path = configPath();
    QFile::remove(path);
    loadFromConfig();
}
