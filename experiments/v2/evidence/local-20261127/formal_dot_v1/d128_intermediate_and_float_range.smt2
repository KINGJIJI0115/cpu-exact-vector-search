; benchmark generated from python API
(set-info :status unknown)
(declare-fun norm () Int)
(declare-fun dot () Int)
(declare-fun dist () Int)
(assert
 (>= norm 0))
(assert
 (<= norm 8323200))
(assert
 (>= dot 0))
(assert
 (<= dot 8323200))
(assert
 (>= dist 0))
(assert
 (<= dist 8323200))
(assert
 (or (>= (+ norm norm) 2147483648) (>= (* 2 dot) 2147483648) (<= (- (+ norm norm) (* 2 dot)) (- 2147483648)) (> dist 16777216)))
(check-sat)
